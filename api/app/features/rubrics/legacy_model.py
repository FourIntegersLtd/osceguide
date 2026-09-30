"""Reading a JSON Schema (a legacy pydantic model, or a v1 rubric's object section) as rubric fields.

Two callers need the same recursion: `scripts/generate_platform_seed.py`, which
turns each exam's legacy model into its version 2 rubric, and
`domain.upgrade_structure`, which turns a version 1 rubric's free-shape object
section into a `group` field on read. Nothing here names an exam's fields: a
field's type comes from its schema, its role from its name (or an explicit
hint), and its description becomes its instructions verbatim.

Pure: no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.features.rubrics.structure import InvalidRubric

__all__ = ["field_from_schema", "humanise", "inline", "ordered_children", "rating_of", "unwrap"]

# A field's role, read from its name when no hint names it: the first rule
# whose words appear in the id wins.
ROLE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("flag", ("critical", "flag", "safety_consideration")),
    ("explanation", ("justification", "explanation")),
    ("evidence", ("phrase", "evidence", "example", "quote")),
    ("strength", ("strength", "completed", "positive")),
    ("improvement", ("improvement", "missed", "negative", "issue")),
    ("action", ("action", "step", "priorit", "suggest")),
)


def humanise(key: str) -> str:
    """A snake_case id as a reader's label."""
    return key.replace("_", " ").capitalize()


def inline(node: Any, definitions: Mapping[str, Any]) -> Any:
    """The schema with every `$ref` replaced by its target; a sibling key wins over the target's."""
    if isinstance(node, Mapping):
        if "$ref" in node:
            target = inline(definitions[str(node["$ref"]).split("/")[-1]], definitions)
            siblings = {key: inline(value, definitions) for key, value in node.items() if key != "$ref"}
            return {**target, **siblings}
        return {key: inline(value, definitions) for key, value in node.items() if key != "$defs"}
    if isinstance(node, list):
        return [inline(item, definitions) for item in node]
    return node


def unwrap(node: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    """A node and whether it is nullable: `anyOf: [X, {type: null}]` is X, nullable."""
    options = node.get("anyOf")
    if isinstance(options, list) and len(options) == 2 and {"type": "null"} in options:
        (inner,) = [option for option in options if option != {"type": "null"}]
        return dict(inner), True
    return dict(node), False


def ordered_children(node: Mapping[str, Any]) -> list[tuple[str, dict[str, Any], bool]]:
    """An object's children as (id, schema, required): required ones first, in the model's order.

    A captured schema may list `properties` alphabetically, but `required`
    keeps the order the model declared its fields in, and that order is part
    of what the marker reads. So required children come in `required` order,
    then the optional ones as listed.
    """
    properties: Mapping[str, Any] = node.get("properties") or {}
    required = [name for name in node.get("required") or [] if name in properties]
    optional = [name for name in properties if name not in required]
    return [(name, dict(properties[name]), name in required) for name in required + optional]


def rating_of(node: Mapping[str, Any]) -> dict[str, Any] | None:
    """The rating a leaf holds, if it is one: a boolean, a bounded number, or single-letter values."""
    if node.get("type") == "boolean":
        return {"kind": "boolean"}
    if node.get("type") in ("number", "integer") and "minimum" in node and "maximum" in node:
        return {
            "kind": "range",
            "minimum": node["minimum"],
            "maximum": node["maximum"],
            "step": "integer" if node["type"] == "integer" else "number",
        }
    values = _single_letter_values(node)
    if values is None:
        return None
    if sorted(values) == ["A", "G", "R"]:
        return {"kind": "rag", "scale": ["G", "A", "R"]}
    return {"kind": "scale", "scale": values}


def _single_letter_values(node: Mapping[str, Any]) -> list[str] | None:
    """The values of a string restricted to single letters (`^[RAG]$`, or an enum of them)."""
    if node.get("type") != "string":
        return None
    enum = node.get("enum")
    if isinstance(enum, list) and enum and all(isinstance(value, str) and len(value) == 1 for value in enum):
        return list(enum)
    match = re.fullmatch(r"\^\[([A-Za-z]+)\]\$", str(node.get("pattern") or ""))
    return list(match[1]) if match else None


def field_from_schema(
    field_id: str,
    node: Mapping[str, Any],
    *,
    required: bool,
    rating_field: str | None = None,
    roles: Mapping[str, str] | None = None,
    system_fields: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """One schema property as a version 2 rubric field, carrying everything the schema said.

    `rating_field` names the competency field that holds the rating: a leaf by
    that name that is a rating becomes a `rating` field. `roles` overrides the
    role read from a field's name, where the name alone is ambiguous.
    `system_fields` lists ids the platform writes, not the marker. Refuses a
    shape the field vocabulary cannot hold rather than guessing at it.
    """
    core, nullable = unwrap(node)
    if nullable and "description" in core:
        raise InvalidRubric(f"{field_id}: a nullable field described on both sides cannot be expressed.")
    field_type = _field_type(field_id, core, rating_field)
    spec: dict[str, Any] = {
        "id": field_id,
        "label": humanise(field_id),
        "type": field_type,
        "required": required,
    }
    spec["role"] = "rating" if field_type == "rating" else _role(field_id, roles)
    if field_id in system_fields:
        spec["source"] = "system"
    if node.get("description"):
        spec["instructions"] = node["description"]
    if nullable:
        spec["nullable"] = True
    for source in (node, core):
        if "default" in source and source["default"] is not None:
            spec["default"] = source["default"]
    if "example" in core:
        spec["example"] = core["example"]
    if "minItems" in core:
        spec["minItems"] = core["minItems"]
    if field_type == "singleSelect":
        spec["options"] = list(core["enum"])
    children_of = core if field_type == "group" else core.get("items") if field_type == "records" else None
    if children_of is not None:
        spec["fields"] = [
            field_from_schema(
                child_id,
                child,
                required=is_required,
                rating_field=rating_field,
                roles=roles,
                system_fields=system_fields,
            )
            for child_id, child, is_required in ordered_children(children_of)
        ]
    return spec


def _role(field_id: str, roles: Mapping[str, str] | None) -> str:
    """What a field is for: a hint when one names it, else its name's first matching rule."""
    if roles and field_id in roles:
        return roles[field_id]
    for role, words in ROLE_RULES:
        if any(word in field_id for word in words):
            return role
    return "other"


def _field_type(field_id: str, core: Mapping[str, Any], rating_field: str | None) -> str:
    """A schema property's answer format."""
    if field_id == rating_field and rating_of(core) is not None:
        return "rating"
    kind = core.get("type")
    if kind == "string":
        if core.get("enum"):
            return "singleSelect"
        long_words = ("explanation", "justification", "explain", "describe", "detail")
        described = str(core.get("description") or "").lower()
        return (
            "longText" if any(word in field_id or word in described for word in long_words) else "shortText"
        )
    if kind == "array":
        items = core.get("items") or {}
        if items == {"type": "string"} or items.get("type") == "string":
            return "list"
        if items.get("type") == "object" and items.get("properties"):
            return "records"
    if kind == "object" and core.get("properties"):
        return "group"
    raise InvalidRubric(
        f"{field_id}: a {kind or 'untyped'} property cannot be expressed as a rubric field "
        "(text, a list of text, a choice, a group or a list of records)."
    )
