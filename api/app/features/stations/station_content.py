"""Station content coverage, AI flattening, and content-vs-structure validation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def station_block_ids(structure: Any) -> list[str]:
    """Every block id declared in a station template structure, in template order."""
    ids: list[str] = []
    if not isinstance(structure, dict):
        return ids
    for section in structure.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks") or []:
            if isinstance(block, dict):
                block_id = block.get("id")
                if isinstance(block_id, str) and block_id:
                    ids.append(block_id)
    return ids


def collect_station_block_ids(structure: Any) -> set[str]:
    """Return all block ids declared in a station template structure."""
    return set(station_block_ids(structure))


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
        """Recurse into a nested section object, pulling out any key that names a known block."""
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
    """Shorten one block's value for a log line: text truncated, structure otherwise left alone."""
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


def _is_media_item(item: Any) -> bool:
    """A bare URL, or `{url, kind?, caption?, alt?}`."""
    return isinstance(item, str) or (isinstance(item, dict) and isinstance(item.get("url"), str))


def _is_media(value: Any) -> bool:
    """One media item, or a list of them."""
    return _is_media_item(value) or (isinstance(value, list) and all(_is_media_item(item) for item in value))


def _is_records(value: Any) -> bool:
    """A list of objects, one per record."""
    return isinstance(value, list) and all(isinstance(record, dict) for record in value)


def _is_qa_list(value: Any) -> bool:
    """A list of `{question, answer}` objects."""
    return isinstance(value, list) and all(
        isinstance(pair, dict) and isinstance(pair.get("question"), str) for pair in value
    )


def _is_grouped_list(value: Any) -> bool:
    """`{group: [text | {title, reasons[]}]}`."""
    if not isinstance(value, dict):
        return False
    for items in value.values():
        if not isinstance(items, list):
            return False
        for item in items:
            if isinstance(item, str):
                continue
            if not isinstance(item, dict) or not isinstance(item.get("title"), str):
                return False
    return True


_RICH_SHAPES: dict[str, tuple[Callable[[Any], bool], str]] = {
    "media": (_is_media, "a media URL, a {url} object, or a list of them"),
    "records": (_is_records, "an array of objects"),
    "qaList": (_is_qa_list, "an array of {question, answer} objects"),
    "groupedList": (_is_grouped_list, "an object of groups, each an array of text or {title, reasons}"),
}


def _text_problems(block: dict[str, Any], value: Any) -> list[str]:
    """A short or long text block holds a string."""
    return [] if isinstance(value, str) else ["must be a string"]


def _array_problems(block: dict[str, Any], value: Any) -> list[str]:
    """A list or multi-select block holds an array."""
    return [] if isinstance(value, list) else ["must be an array"]


def _checklist_problems(block: dict[str, Any], value: Any) -> list[str]:
    """A checklist holds the ids of the items that were ticked."""
    return [] if isinstance(value, list) else ["must be an array of item ids"]


def _single_select_problems(block: dict[str, Any], value: Any) -> list[str]:
    """A single-select holds one of the block's options, or any string when it lists none."""
    options = [str(option) for option in (block.get("options") or []) if option is not None]
    if isinstance(value, str) and (not options or value in options):
        return []
    return [f"must be one of: {options}"]


def _scale_problems(block: dict[str, Any], value: Any) -> list[str]:
    """A scale holds a number inside the block's own minimum and maximum."""
    if not isinstance(value, (int, float)):
        return ["must be a number"]
    problems: list[str] = []
    minimum = block.get("min")
    maximum = block.get("max")
    if isinstance(minimum, (int, float)) and value < minimum:
        problems.append(f"must be >= {minimum}")
    if isinstance(maximum, (int, float)) and value > maximum:
        problems.append(f"must be <= {maximum}")
    return problems


def _rich_problems(block: dict[str, Any], value: Any) -> list[str]:
    """A media, records, question-and-answer or grouped block holds that block's own shape."""
    has_shape, shape_in_words = _RICH_SHAPES[str(block.get("type"))]
    return [] if has_shape(value) else [f"must be {shape_in_words}"]


# What is wrong with a value, by the type of block it fills. Each check answers
# with the rest of the sentence "Block '<id>' ...", and with nothing when the
# value fits. A block type that is not listed accepts any value.
_BLOCK_CHECKS: dict[str, Callable[[dict[str, Any], Any], list[str]]] = {
    "shortText": _text_problems,
    "longText": _text_problems,
    "list": _array_problems,
    "multiSelect": _array_problems,
    "checklist": _checklist_problems,
    "singleSelect": _single_select_problems,
    "scale": _scale_problems,
    **dict.fromkeys(_RICH_SHAPES, _rich_problems),
}


def _template_blocks(structure: dict[str, Any]) -> list[dict[str, Any]]:
    """Every block of a template that has an id, section by section, skipping anything malformed."""
    return [
        block
        for section in structure.get("sections") or []
        if isinstance(section, dict)
        for block in section.get("blocks") or []
        if isinstance(block, dict) and block.get("id")
    ]


def validate_station_content(structure: Any, content: Any) -> tuple[bool, list[str]]:
    """Check a station's content against its template: whether it fits, and what does not.

    A required block must be filled. A block that is filled must hold the
    shape its type calls for. A block left empty and not required is fine.
    """
    if not isinstance(content, dict):
        return False, ["content must be an object"]
    if not isinstance(structure, dict):
        return False, ["structure must be an object"]

    errors: list[str] = []
    for block in _template_blocks(structure):
        block_id = block["id"]
        value = content.get(block_id)
        if block.get("required") and is_station_block_value_empty(value):
            errors.append(f"Block '{block_id}' is required but missing or empty")
            continue
        check = _BLOCK_CHECKS.get(str(block.get("type")))
        if value is None or check is None:
            continue
        errors.extend(f"Block '{block_id}' {problem}" for problem in check(block, value))
    return len(errors) == 0, errors


# What a block keeps of its role in a `faculty` section: the marker's notes stay
# the marker's and the debrief tutor's points stay the tutor's.
_ROLES_KEPT_IN_FACULTY = ("examiner", "debrief")


def engine_layout(blocks: list[Any], sections: list[Any]) -> list[dict[str, Any]]:
    """The block list the engine places by role, completed from the template's sections.

    The flat `blocks` list the template editor saves carries only id, label and
    role. What else the engine needs is in the sections: a block's type and a
    table's columns, without which a table's rows are read as bare values and a
    grouped list loses its group names, and the section's audience. Every block
    of a `faculty` section is given the `faculty` role, so a block an author
    left without a role there is not read to the patient as a leftover. An
    `examiner` or `debrief` block keeps its role wherever it is filed, as it
    does for the audiences (`domain_audience`).
    """
    described: dict[str, dict[str, Any]] = {}
    faculty_ids: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            continue
        for block in section.get("blocks") or []:
            if not isinstance(block, dict) or not block.get("id"):
                continue
            described[str(block["id"])] = {key: block[key] for key in ("type", "fields") if key in block}
            if section.get("audience") == "faculty":
                faculty_ids.add(str(block["id"]))
    layout: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = str(block.get("id") or "")
        placed = described.get(block_id, {}) | block
        if block_id in faculty_ids and placed.get("role") not in _ROLES_KEPT_IN_FACULTY:
            placed["role"] = "faculty"
        layout.append(placed)
    return layout


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
                if block.get("type") == "records" and isinstance(block.get("fields"), list):
                    # Without its columns a model cannot know what one row of the table holds.
                    compact_block["fields"] = block.get("fields")
                if block.get("type") == "groupedList" and isinstance(block.get("groups"), list):
                    compact_block["groups"] = block.get("groups")
                if block.get("type") == "scale":
                    compact_block["min"] = block.get("min")
                    compact_block["max"] = block.get("max")
                compact_blocks.append(compact_block)
        compact_sections.append(
            {"id": section.get("id"), "title": section.get("title"), "blocks": compact_blocks}
        )
    return {"schemaVersion": structure.get("schemaVersion", 1), "sections": compact_sections}
