"""Station content coverage, AI flattening, and content-vs-structure validation."""

from __future__ import annotations

from typing import Any


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
                block_id = block.get("id")
                if isinstance(block_id, str) and block_id:
                    ids.add(block_id)
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
            block_id = block.get("id")
            if isinstance(block_id, str) and block_id and bool(block.get("required")):
                required.append(block_id)
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

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        for key, block_value in node.items():
            if key in block_ids:
                flat[key] = block_value
            elif isinstance(block_value, dict):
                walk(block_value)

    walk(content)

    for key, block_value in payload.items():
        if key in block_ids and key not in flat:
            flat[key] = block_value

    return flat


def _preview_block_value(value: Any, *, max_str: int = 120) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.replace("\n", " ").strip()
        if len(text) > max_str:
            return text[:max_str] + f"...({len(text)} chars)"
        return text
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

    for block_id in sorted(all_ids):
        block_value = content.get(block_id)
        is_empty = is_station_block_value_empty(block_value)
        if is_empty:
            if block_id in content:
                present_but_empty.append(block_id)
            if block_id in required:
                missing_required.append(block_id)
            else:
                missing_optional.append(block_id)
        else:
            populated.append(block_id)
            field_previews[block_id] = _preview_block_value(block_value)

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
            block_id = block.get("id")
            block_type = block.get("type")
            required = bool(block.get("required"))

            if not block_id:
                continue

            value = content.get(block_id)

            if required and is_station_block_value_empty(value):
                errors.append(f"Block '{block_id}' is required but missing or empty")
                continue

            if value is None:
                continue

            if block_type in ("shortText", "longText") and not isinstance(value, str):
                errors.append(f"Block '{block_id}' must be a string")
            elif block_type == "list" and not isinstance(value, list):
                errors.append(f"Block '{block_id}' must be an array")
            elif block_type == "singleSelect":
                options = [str(option) for option in (block.get("options") or []) if option is not None]
                if not isinstance(value, str) or (options and value not in options):
                    errors.append(f"Block '{block_id}' must be one of: {options}")
            elif block_type == "multiSelect":
                if not isinstance(value, list):
                    errors.append(f"Block '{block_id}' must be an array")
            elif block_type == "checklist":
                if not isinstance(value, list):
                    errors.append(f"Block '{block_id}' must be an array of item ids")
            elif block_type == "scale":
                if not isinstance(value, (int, float)):
                    errors.append(f"Block '{block_id}' must be a number")
                else:
                    minimum = block.get("min")
                    maximum = block.get("max")
                    if isinstance(minimum, (int, float)) and value < minimum:
                        errors.append(f"Block '{block_id}' must be >= {minimum}")
                    if isinstance(maximum, (int, float)) and value > maximum:
                        errors.append(f"Block '{block_id}' must be <= {maximum}")

    return len(errors) == 0, errors


def structure_spec(structure: Any) -> dict[str, Any]:
    """Compact template shape sent to the model for autogeneration."""
    if not isinstance(structure, dict):
        return {}
    sections = structure.get("sections")
    if not isinstance(sections, list):
        return {"schemaVersion": structure.get("schemaVersion", 1), "sections": []}
    compact_sections: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        blocks = section.get("blocks")
        compact_blocks: list[dict[str, Any]] = []
        if isinstance(blocks, list):
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                compact_block: dict[str, Any] = {
                    "id": block.get("id"),
                    "type": block.get("type"),
                    "label": block.get("label"),
                    "required": bool(block.get("required")),
                }
                if block.get("type") in ("singleSelect", "multiSelect") and isinstance(
                    block.get("options"), list
                ):
                    compact_block["options"] = block.get("options")
                if block.get("type") == "checklist" and isinstance(block.get("items"), list):
                    checklist_items = block["items"]
                    compact_block["items"] = [
                        {"id": checklist_item.get("id"), "label": checklist_item.get("label")}
                        for checklist_item in checklist_items
                        if isinstance(checklist_item, dict)
                    ]
                if block.get("type") == "scale":
                    compact_block["min"] = block.get("min")
                    compact_block["max"] = block.get("max")
                compact_blocks.append(compact_block)
        compact_sections.append(
            {"id": section.get("id"), "title": section.get("title"), "blocks": compact_blocks}
        )
    return {"schemaVersion": structure.get("schemaVersion", 1), "sections": compact_sections}
