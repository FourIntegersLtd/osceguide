"""Resolve system prompts and per-block hints for station autogenerate."""

from __future__ import annotations

from typing import Any

from app.features.stations.generation_profiles.platform_overrides import (
    PLATFORM_BLOCK_HINT_OVERRIDES,
)
from app.features.stations.generation_profiles.registry import (
    get_profile,
    resolve_profile_key_from_structure,
)
from app.features.stations.generation_profiles.template_block_hint_supplements import (
    TEMPLATE_BLOCK_HINT_SUPPLEMENTS,
)


def resolve_system_prompt(
    structure: dict[str, Any],
    *,
    exam_code: str | None,
    allow_custom_override: bool,
) -> str:
    profile_key = resolve_profile_key_from_structure(structure, exam_code)
    raw_generation = structure.get("generation")
    generation: dict[str, Any] = raw_generation if isinstance(raw_generation, dict) else {}

    if allow_custom_override and profile_key == "custom":
        override = generation.get("systemPromptOverride")
        if isinstance(override, str) and override.strip():
            base = override.strip()
        else:
            base = "You generate OSCE station content for the given template."
    else:
        profile = get_profile(profile_key)
        if profile is not None and profile.meta.profile_key != "custom":
            base = profile.system_prompt().strip()
        else:
            from app.features.generation.service import station_system_prompt

            base = station_system_prompt(exam_code).strip()

    append = generation.get("systemPromptAppend")
    if isinstance(append, str) and append.strip():
        return f"{base}\n\n{append.strip()}"
    return base


def effective_block_hints_for_profile(profile_key: str) -> dict[str, str]:
    """Catalog hints for the template builder: profile JSON + supplements + overrides."""
    profile = get_profile(profile_key)
    merged: dict[str, str] = dict(profile.block_hints) if profile else {}
    for block_id, hint in TEMPLATE_BLOCK_HINT_SUPPLEMENTS.items():
        merged.setdefault(block_id, hint)
    for block_id, hint in PLATFORM_BLOCK_HINT_OVERRIDES.items():
        merged[block_id] = hint
    return merged


def resolve_block_generation_hints(
    structure: Any,
    *,
    profile_key: str,
) -> dict[str, str]:
    """Merge profile hints, platform overrides, block.generationHint, and placeholder."""
    if not isinstance(structure, dict):
        return {}

    profile = get_profile(profile_key)
    profile_hints: dict[str, str] = dict(profile.block_hints) if profile else {}

    hints: dict[str, str] = {}
    for section in structure.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            block_id = block.get("id")
            if not isinstance(block_id, str) or not block_id.strip():
                continue
            if block_id.startswith("clinical_analysis_") or block_id.endswith("_feedback"):
                continue

            custom = block.get("generationHint")
            if isinstance(custom, str) and custom.strip():
                hints[block_id] = custom.strip()
                continue

            parts: list[str] = []
            if block_id in PLATFORM_BLOCK_HINT_OVERRIDES:
                parts.append(PLATFORM_BLOCK_HINT_OVERRIDES[block_id])
            elif block_id in profile_hints:
                parts.append(profile_hints[block_id])
            elif block_id in TEMPLATE_BLOCK_HINT_SUPPLEMENTS:
                parts.append(TEMPLATE_BLOCK_HINT_SUPPLEMENTS[block_id])

            placeholder = block.get("placeholder")
            if isinstance(placeholder, str) and placeholder.strip():
                parts.append(f"Author guidance: {placeholder.strip()}")

            if parts:
                hints[block_id] = "\n\n".join(parts)
                continue

            label = block.get("label")
            if isinstance(label, str) and label.strip():
                hints[block_id] = f"Fill this field ({label.strip()}) with realistic exam content."

    return hints


def profile_key_for_structure(structure: dict[str, Any], exam_code: str | None) -> str:
    return resolve_profile_key_from_structure(structure, exam_code)
