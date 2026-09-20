"""AI autogenerate draft content for station instances."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.logging import get_logger
from app.core.settings import Settings
from app.features.catalog.service import exam_code_by_id
from app.features.generation.errors import GenerationUnavailable
from app.features.stations import repository_templates as template_repository
from app.features.stations import service_templates as templates
from app.features.stations.generation_profiles.resolve import (
    profile_key_for_structure,
    resolve_system_prompt,
)
from app.features.stations.station_ai import generate_station_autogenerate
from app.features.stations.station_block_hints import hints_for_structure
from app.features.stations.station_content import (
    collect_required_station_block_ids,
    collect_station_block_ids,
    normalize_station_ai_content,
    should_retry_sparse_station_content,
    structure_spec,
    summarize_station_content_coverage,
    validate_station_content,
)
from app.features.stations.station_validator import validate_station_structure

logger = get_logger(__name__)


_TEMPLATE_AUTOGENERATE_RULES = (
    "You generate complete OSCE station content for a given template.\n"
    "Return JSON only. No markdown.\n\n"
    "Output shape:\n"
    '{ "title": string, "blocks": [ { "blockId": string, '
    '"value": string | string[] | number | boolean }, ... ] }\n\n'
    "Rules:\n"
    "- blocks MUST include one object for EVERY blockId from allBlockIds (required AND optional).\n"
    "- blockId must match templateStructure exactly. Do NOT nest values by section title.\n"
    "- Do NOT use empty strings or empty arrays as placeholders. Fill every block with "
    "realistic exam content derived from the prompt.\n"
    "- list fields: 2–6 concise bullet strings each.\n"
    "- longText/shortText: non-empty prose (persona, explanation, safety netting, etc.).\n"
    "- singleSelect: one of the provided options (string).\n"
    "- multiSelect: array of provided options (strings).\n"
    "- checklist: array of item ids (strings).\n"
    "- scale: number between min and max.\n"
    "- Clinician pack and management sections must be as detailed as patient information.\n\n"
    "Patient pack — opening_sentence (CRITICAL):\n"
    "- Write a SHORT first-person line the AI simulated patient speaks to start the consultation.\n"
    "- Do NOT prefix with 'Hi doctor' / 'Hello' — the session speaks its own greeting first.\n"
    "- Do NOT put the full history in opening_sentence; use expanded_history "
    "for details revealed when asked.\n"
    "- 1–3 sentences, natural spoken English; '...' pauses allowed.\n"
    "- Follow blockGenerationHints.opening_sentence when present.\n\n"
    "Doctor information — recent_notes (CRITICAL):\n"
    "- Candidate-facing prior documentation: past GP/clinic visits only.\n"
    "- Never recap the acute presentation or point toward the diagnosis.\n"
    "- Prefer 'No recent GP visits' or mundane unrelated visits when appropriate.\n"
    "- Follow blockGenerationHints.recent_notes when present.\n"
)


async def _exam_code_for_template_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    template_version: Any,
) -> str:
    template = await template_repository.template_by_id(session, org_id, template_version.template_id)
    if template is None or template.exam_id is None:
        return "sca"
    return await exam_code_by_id(session, template.exam_id) or "sca"


async def autogenerate_station_draft(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    prompt: str,
    template_version_id: uuid.UUID,
    settings: Settings,
) -> dict[str, Any]:
    """Return ``suggested_title`` and ``content`` keyed by template block ids."""
    if not prompt.strip():
        raise InvalidInput("prompt is required")

    row = await templates.bindable_version(session, org_id, template_version_id)
    structure = dict(row.structure)

    ok_struct, errs_struct = validate_station_structure(structure)
    if not ok_struct:
        raise InvalidInput(f"Template structure invalid: {errs_struct}")

    spec = structure_spec(structure)
    exam_code = await _exam_code_for_template_version(session, org_id, row)
    profile_key = profile_key_for_structure(structure, exam_code)
    block_hints = hints_for_structure(structure, exam_code=exam_code)
    required_block_ids = collect_required_station_block_ids(structure)
    all_block_ids = sorted(collect_station_block_ids(structure))
    logger.info(
        "[PLATFORM_AUTOGENERATE] start org_id=%s template_version=%s exam_code=%s profile=%s "
        "prompt_len=%d blocks=%d required=%d",
        org_id,
        template_version_id,
        exam_code,
        profile_key,
        len(prompt),
        len(all_block_ids),
        len(required_block_ids),
    )

    generation_started = time.monotonic()
    allow_custom = org_id is not None
    system = (
        resolve_system_prompt(
            structure,
            exam_code=exam_code,
            allow_custom_override=allow_custom,
        )
        + "\n\n"
        + _TEMPLATE_AUTOGENERATE_RULES
    )
    user = json.dumps(
        {
            "templateVersionId": str(template_version_id),
            "templateStructure": spec,
            "requiredBlockIds": required_block_ids,
            "allBlockIds": all_block_ids,
            "blockGenerationHints": block_hints,
            "prompt": prompt,
        }
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    suggested_title = ""
    content: dict[str, Any] = {}
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        parsed, parse_err = await generate_station_autogenerate(messages, settings=settings)
        if parsed is None:
            if attempt >= max_attempts:
                msg = parse_err or "AI generation failed"
                if "OpenAI is not configured" in msg:
                    raise GenerationUnavailable()
                raise GenerationUnavailable(msg)
            continue

        ai_payload = parsed.model_dump(by_alias=True)
        suggested_title = str(parsed.title or "")
        content = normalize_station_ai_content(
            structure,
            {"title": parsed.title, "content": parsed.content_map()},
        )
        ok_content, errs = validate_station_content(structure, content)
        if not ok_content:
            if attempt >= max_attempts:
                raise InvalidInput(f"Generated content did not match template: {errs}")
            messages.append({"role": "assistant", "content": json.dumps(ai_payload)})
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "validationErrors": errs,
                            "requiredBlockIds": required_block_ids,
                            "instruction": (
                                "Your previous JSON failed validation. Return corrected JSON only. "
                                "blocks must include every requiredBlockId with blockId and value."
                            ),
                        }
                    ),
                }
            )
            continue

        coverage = summarize_station_content_coverage(structure, content)
        if should_retry_sparse_station_content(coverage):
            if attempt >= max_attempts:
                break
            empty_blocks = (
                coverage.get("presentButEmptyBlockIds") or coverage.get("missingOptionalBlockIds") or []
            )
            messages.append({"role": "assistant", "content": json.dumps(ai_payload)})
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "emptyBlockIds": empty_blocks,
                            "allBlockIds": all_block_ids,
                            "instruction": (
                                "Your previous JSON included entries but left many blocks as empty "
                                "strings or empty arrays. Regenerate the FULL station. Every block "
                                "in allBlockIds must appear in blocks with realistic exam content: "
                                "lists need 2–6 items, text fields need prose. Do not use [] or "
                                '"" placeholders.'
                            ),
                        }
                    ),
                }
            )
            continue
        break

    final_coverage = summarize_station_content_coverage(structure, content)
    elapsed_s = round(time.monotonic() - generation_started, 1)
    logger.info(
        "[PLATFORM_AUTOGENERATE] success template_version=%s title=%r elapsed_s=%s populated=%d/%d",
        template_version_id,
        suggested_title.strip(),
        elapsed_s,
        final_coverage.get("populatedCount"),
        final_coverage.get("totalBlocks"),
    )

    return {
        "suggested_title": suggested_title.strip(),
        "content": content,
    }
