"""Station template structure/content validation and AI autogenerate helpers."""

from __future__ import annotations

from typing import Any

_VALID_BLOCK_TYPES = frozenset(
    {
        "shortText",
        "longText",
        "list",
        "singleSelect",
        "multiSelect",
        "checklist",
        "scale",
        "ragCriterion",
        # Rich types: the type also says how the block is drawn, so a new exam's
        # layout is template data rather than a screen of its own.
        "media",
        "records",
        "qaList",
        "groupedList",
    }
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
            profile_key = generation.get("profileKey")
            if profile_key is not None and (not isinstance(profile_key, str) or not profile_key.strip()):
                errors.append("structure.generation.profileKey must be a non-empty string when set")
            for key in ("systemPromptAppend", "systemPromptOverride"):
                prompt_value = generation.get(key)
                if prompt_value is not None and not isinstance(prompt_value, str):
                    errors.append(f"structure.generation.{key} must be a string when set")
                elif isinstance(prompt_value, str) and len(prompt_value) > 20_000:
                    errors.append(f"structure.generation.{key} exceeds maximum length (20000)")

    if len(sections) == 0:
        errors.append("structure.sections: at least one section is required")

    block_ids_seen: set[str] = set()

    for section_index, section in enumerate(sections):
        if not isinstance(section, dict):
            errors.append(f"sections[{section_index}] must be an object")
            continue

        if not section.get("id"):
            errors.append(f"sections[{section_index}].id is required")

        if "readingBriefDefault" in section and not isinstance(section.get("readingBriefDefault"), bool):
            errors.append(f"sections[{section_index}].readingBriefDefault must be a boolean when present")

        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            errors.append(f"sections[{section_index}].blocks must be an array")
            continue

        for block_index, block in enumerate(blocks):
            block_path = f"sections[{section_index}].blocks[{block_index}]"
            if not isinstance(block, dict):
                errors.append(f"{block_path} must be an object")
                continue

            block_id = block.get("id")
            if not block_id:
                errors.append(f"{block_path}.id is required")
            elif block_id in block_ids_seen:
                errors.append(f"{block_path}.id: duplicate block id: {block_id}")
            else:
                block_ids_seen.add(block_id)

            if "readingBrief" in block and not isinstance(block.get("readingBrief"), bool):
                errors.append(f"{block_path}.readingBrief must be a boolean when present")

            block_type = block.get("type")
            if block_type not in _VALID_BLOCK_TYPES:
                errors.append(f"{block_path}.type: invalid block type '{block_type}'")
                continue

            if block_type in ("singleSelect", "multiSelect"):
                options = block.get("options")
                if not isinstance(options, list) or len(options) == 0:
                    errors.append(f"{block_path}.options is required for select blocks")

            if block_type == "checklist":
                items = block.get("items")
                if not isinstance(items, list) or len(items) == 0:
                    errors.append(f"{block_path}.items is required for checklist blocks")

            if block_type == "scale" and (
                not isinstance(block.get("min"), (int, float))
                or not isinstance(block.get("max"), (int, float))
            ):
                errors.append(f"{block_path} scale block requires numeric min and max")

            if block_type == "ragCriterion":
                path_stem = block.get("pathStem")
                if not isinstance(path_stem, str) or not path_stem.strip():
                    errors.append(f"{block_path}.pathStem is required for ragCriterion blocks")

            if block_type == "records" and "fields" in block:
                fields = block.get("fields")
                if not isinstance(fields, list) or not all(
                    isinstance(record_field, dict)
                    and isinstance(record_field.get("key"), str)
                    and record_field["key"].strip()
                    for record_field in fields
                ):
                    errors.append(f"{block_path}.fields must be a list of {{key, label}} objects")

            generation_hint = block.get("generationHint")
            if generation_hint is not None and not isinstance(generation_hint, str):
                errors.append(f"{block_path}.generationHint must be a string when set")
            elif isinstance(generation_hint, str) and len(generation_hint) > 8_000:
                errors.append(f"{block_path}.generationHint exceeds maximum length (8000)")

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
