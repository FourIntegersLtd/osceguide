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
                errors.append(
                    f"sections[{s_idx}].blocks[{b_idx}].type: invalid block type '{btype}'"
                )
                continue

            if btype in ("singleSelect", "multiSelect"):
                opts = block.get("options")
                if not isinstance(opts, list) or len(opts) == 0:
                    errors.append(
                        f"sections[{s_idx}].blocks[{b_idx}].options is required for select blocks"
                    )

            if btype == "checklist":
                items = block.get("items")
                if not isinstance(items, list) or len(items) == 0:
                    errors.append(
                        f"sections[{s_idx}].blocks[{b_idx}].items is required for checklist blocks"
                    )

            if btype == "scale":
                if not isinstance(block.get("min"), (int, float)) or not isinstance(
                    block.get("max"), (int, float)
                ):
                    errors.append(
                        f"sections[{s_idx}].blocks[{b_idx}] scale block requires numeric min and max"
                    )

            if btype == "ragCriterion":
                path_stem = block.get("pathStem")
                if not isinstance(path_stem, str) or not path_stem.strip():
                    errors.append(
                        f"sections[{s_idx}].blocks[{b_idx}].pathStem is required for ragCriterion blocks"
                    )

            gen_hint = block.get("generationHint")
            if gen_hint is not None and not isinstance(gen_hint, str):
                errors.append(
                    f"sections[{s_idx}].blocks[{b_idx}].generationHint must be a string when set"
                )
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
        errors.append(
            "structure.generation.systemPromptOverride is only allowed when profileKey is 'custom'"
        )
    if org_id is None and override.strip():
        errors.append(
            "structure.generation.systemPromptOverride is not allowed on platform-owned templates"
        )
    return errors


def collect_station_block_ids(structure: Any) -> set[str]:
    """Return all block ids declared in a station template structure."""
    ids: set[str] = set()
    if not isinstance(structure, dict):
        return ids
    for section in structure.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks") or []:
            if isinstance(block, dict):
                bid = block.get("id")
                if isinstance(bid, str) and bid:
                    ids.add(bid)
    return ids


def collect_required_station_block_ids(structure: Any) -> list[str]:
    """Return required block ids in template order."""
    required: list[str] = []
    if not isinstance(structure, dict):
        return required
    for section in structure.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            bid = block.get("id")
            if isinstance(bid, str) and bid and bool(block.get("required")):
                required.append(bid)
    return required


def normalize_station_ai_content(structure: Any, payload: Any) -> dict[str, Any]:
    """Flatten AI JSON into blockId -> value map (handles nested section objects)."""
    block_ids = collect_station_block_ids(structure)
    if not block_ids or not isinstance(payload, dict):
        return {}

    content = payload.get("content")
    if not isinstance(content, dict):
        content = payload

    flat: dict[str, Any] = {}

    def walk(obj: Any) -> None:
        if not isinstance(obj, dict):
            return
        for key, val in obj.items():
            if key in block_ids:
                flat[key] = val
            elif isinstance(val, dict):
                walk(val)

    walk(content)

    for key, val in payload.items():
        if key in block_ids and key not in flat:
            flat[key] = val

    return flat


def _preview_block_value(value: Any, *, max_str: int = 120) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.replace("\n", " ").strip()
        if len(s) > max_str:
            return s[:max_str] + f"...({len(s)} chars)"
        return s
    if isinstance(value, list):
        return {"type": "list", "count": len(value), "sample": value[:3]}
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, dict):
        return {"type": "object", "keys": sorted(value.keys())[:20]}
    return {"type": type(value).__name__}


def is_station_block_value_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def should_retry_sparse_station_content(coverage: dict[str, Any]) -> bool:
    """True when AI returned keys but left many optional blocks empty."""
    optional_count = int(coverage.get("optionalCount") or 0)
    if optional_count == 0:
        return False
    missing_optional = coverage.get("missingOptionalBlockIds") or []
    return len(missing_optional) > optional_count // 2


def summarize_station_content_coverage(structure: Any, content: Any) -> dict[str, Any]:
    """Compare generated content against template blocks for logging/debug."""
    all_ids = collect_station_block_ids(structure)
    required = set(collect_required_station_block_ids(structure))
    optional = sorted(all_ids - required)

    populated: list[str] = []
    present_but_empty: list[str] = []
    missing_required: list[str] = []
    missing_optional: list[str] = []
    field_previews: dict[str, Any] = {}

    if not isinstance(content, dict):
        content = {}

    for bid in sorted(all_ids):
        val = content.get(bid)
        is_empty = is_station_block_value_empty(val)
        if is_empty:
            if bid in content:
                present_but_empty.append(bid)
            if bid in required:
                missing_required.append(bid)
            else:
                missing_optional.append(bid)
        else:
            populated.append(bid)
            field_previews[bid] = _preview_block_value(val)

    return {
        "totalBlocks": len(all_ids),
        "requiredCount": len(required),
        "optionalCount": len(optional),
        "populatedCount": len(populated),
        "populatedBlockIds": populated,
        "presentButEmptyBlockIds": present_but_empty,
        "missingRequiredBlockIds": missing_required,
        "missingOptionalBlockIds": missing_optional,
        "fieldPreviews": field_previews,
    }


def validate_station_content(structure: Any, content: Any) -> tuple[bool, list[str]]:
    """Validate that content matches the station template structure."""
    errors: list[str] = []

    if not isinstance(content, dict):
        return False, ["content must be an object"]

    if not isinstance(structure, dict):
        return False, ["structure must be an object"]

    sections = structure.get("sections") or []
    for section in sections:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            bid = block.get("id")
            btype = block.get("type")
            required = bool(block.get("required"))

            if not bid:
                continue

            value = content.get(bid)

            if required and is_station_block_value_empty(value):
                errors.append(f"Block '{bid}' is required but missing or empty")
                continue

            if value is None:
                continue

            if btype in ("shortText", "longText") and not isinstance(value, str):
                errors.append(f"Block '{bid}' must be a string")
            elif btype == "list" and not isinstance(value, list):
                errors.append(f"Block '{bid}' must be an array")
            elif btype == "singleSelect":
                opts = [str(o) for o in (block.get("options") or []) if o is not None]
                if not isinstance(value, str) or (opts and value not in opts):
                    errors.append(f"Block '{bid}' must be one of: {opts}")
            elif btype == "multiSelect":
                if not isinstance(value, list):
                    errors.append(f"Block '{bid}' must be an array")
            elif btype == "checklist":
                if not isinstance(value, list):
                    errors.append(f"Block '{bid}' must be an array of item ids")
            elif btype == "scale":
                if not isinstance(value, (int, float)):
                    errors.append(f"Block '{bid}' must be a number")
                else:
                    mn = block.get("min")
                    mx = block.get("max")
                    if isinstance(mn, (int, float)) and value < mn:
                        errors.append(f"Block '{bid}' must be >= {mn}")
                    if isinstance(mx, (int, float)) and value > mx:
                        errors.append(f"Block '{bid}' must be <= {mx}")

    return len(errors) == 0, errors
