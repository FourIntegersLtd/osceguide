"""Station template structure/content validation and AI autogenerate helpers."""

from __future__ import annotations

from typing import Any

_VALID_BLOCK_TYPES = frozenset(
    {"shortText", "longText", "list", "singleSelect", "multiSelect", "checklist", "scale", "ragCriterion"}
)


def validate_station_structure(structure: Any) -> tuple[bool, list[str]]:
    """Validate a station template structure dict."""
    errors: list[str] = []

    if not isinstance(structure, dict):
        return False, ["structure must be an object"]

    sections = structure.get("sections")
    if not isinstance(sections, list):
        return False, ["structure.sections must be an array"]

    generation = structure.get("generation")
    if generation is not None:
        if not isinstance(generation, dict):
            errors.append("structure.generation must be an object when present")
        else:
            pk = generation.get("profileKey")
            if pk is not None and (not isinstance(pk, str) or not pk.strip()):
                errors.append("structure.generation.profileKey must be a non-empty string when set")
            for key in ("systemPromptAppend", "systemPromptOverride"):
                val = generation.get(key)
                if val is not None and not isinstance(val, str):
                    errors.append(f"structure.generation.{key} must be a string when set")
                elif isinstance(val, str) and len(val) > 20_000:
                    errors.append(f"structure.generation.{key} exceeds maximum length (20000)")

    if len(sections) == 0:
        errors.append("structure.sections: at least one section is required")

    block_ids_seen: set[str] = set()

    for s_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"sections[{s_idx}] must be an object")
            continue

        if not section.get("id"):
            errors.append(f"sections[{s_idx}].id is required")

        if "readingBriefDefault" in section and not isinstance(section.get("readingBriefDefault"), bool):
            errors.append(f"sections[{s_idx}].readingBriefDefault must be a boolean when present")

        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            errors.append(f"sections[{s_idx}].blocks must be an array")
            continue

        for b_idx, block in enumerate(blocks):
            if not isinstance(block, dict):
                errors.append(f"sections[{s_idx}].blocks[{b_idx}] must be an object")
                continue

            bid = block.get("id")
            if not bid:
                errors.append(f"sections[{s_idx}].blocks[{b_idx}].id is required")
            elif bid in block_ids_seen:
                errors.append(f"sections[{s_idx}].blocks[{b_idx}].id: duplicate block id: {bid}")
            else:
                block_ids_seen.add(bid)

            if "readingBrief" in block and not isinstance(block.get("readingBrief"), bool):
                errors.append(
                    f"sections[{s_idx}].blocks[{b_idx}].readingBrief must be a boolean when present"
                )

            btype = block.get("type")
            if btype not in _VALID_BLOCK_TYPES:
                errors.append(f"sections[{s_idx}].blocks[{b_idx}].type: invalid block type '{btype}'")
                continue

            if btype in ("singleSelect", "multiSelect"):
                opts = block.get("options")
                if not isinstance(opts, list) or len(opts) == 0:
                    errors.append(f"sections[{s_idx}].blocks[{b_idx}].options is required for select blocks")

            if btype == "checklist":
                items = block.get("items")
                if not isinstance(items, list) or len(items) == 0:
                    errors.append(f"sections[{s_idx}].blocks[{b_idx}].items is required for checklist blocks")

            if btype == "scale" and (
                not isinstance(block.get("min"), (int, float))
                or not isinstance(block.get("max"), (int, float))
            ):
                errors.append(f"sections[{s_idx}].blocks[{b_idx}] scale block requires numeric min and max")

            if btype == "ragCriterion":
                path_stem = block.get("pathStem")
                if not isinstance(path_stem, str) or not path_stem.strip():
                    errors.append(
                        f"sections[{s_idx}].blocks[{b_idx}].pathStem is required for ragCriterion blocks"
                    )

            gen_hint = block.get("generationHint")
            if gen_hint is not None and not isinstance(gen_hint, str):
                errors.append(f"sections[{s_idx}].blocks[{b_idx}].generationHint must be a string when set")
            elif isinstance(gen_hint, str) and len(gen_hint) > 8_000:
                errors.append(
                    f"sections[{s_idx}].blocks[{b_idx}].generationHint exceeds maximum length (8000)"
                )

    return len(errors) == 0, errors


def validate_generation_policy(
    structure: dict[str, Any],
    *,
    org_id: object,
) -> list[str]:
    """Org vs platform rules for custom system prompts."""
    errors: list[str] = []
    generation = structure.get("generation")
    if not isinstance(generation, dict):
        return errors
    override = generation.get("systemPromptOverride")
    if not isinstance(override, str) or not override.strip():
        return errors
    profile_key = generation.get("profileKey")
    if profile_key != "custom":
        errors.append("structure.generation.systemPromptOverride is only allowed when profileKey is 'custom'")
    if org_id is None and override.strip():
        errors.append("structure.generation.systemPromptOverride is not allowed on platform-owned templates")
    return errors
