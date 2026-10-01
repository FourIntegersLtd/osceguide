"""Build a minimal payload that satisfies a JSON Schema.

For consumers and tests that need a result shaped like a framework's schema
without calling a model. Only required properties are populated; optional
ones are left out, which is the smallest payload a marker could return.
"""

from __future__ import annotations

import re
from typing import Any

_MAX_DEPTH = 40
_PATTERN_CANDIDATES = ("R", "A", "G", "example", "2026-09-14T12:00:00Z", "2026-09-14", "1", "x")


def example_payload_for(schema: dict[str, Any]) -> Any:
    return _build(schema, schema.get("$defs", {}), depth=0)


def _resolve(node: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Follow ``$ref`` links until reaching a schema node that is not a reference."""
    while "$ref" in node:
        node = defs[node["$ref"].rsplit("/", 1)[-1]]
    return node


def _build(node: dict[str, Any], defs: dict[str, Any], *, depth: int) -> Any:
    """Build the smallest valid value for one schema node, recursing into nested nodes."""
    if depth > _MAX_DEPTH:
        raise RecursionError("schema nesting exceeds the example generator's limit")
    node = _resolve(node, defs)
    if "const" in node:
        return node["const"]
    if "enum" in node:
        return node["enum"][0]
    for combinator in ("anyOf", "oneOf"):
        if combinator in node:
            options = [_resolve(option, defs) for option in node[combinator]]
            preferred = [option for option in options if option.get("type") != "null"] or options
            return _build(preferred[0], defs, depth=depth + 1)
    if "allOf" in node:
        merged: dict[str, Any] = {}
        for part in node["allOf"]:
            merged.update(_resolve(part, defs))
        return _build(merged, defs, depth=depth + 1)
    kind = node.get("type")
    if isinstance(kind, list):
        kind = next((entry for entry in kind if entry != "null"), kind[0])
    if kind is None and "properties" in node:
        kind = "object"
    if kind == "object":
        properties = node.get("properties", {})
        return {name: _build(properties[name], defs, depth=depth + 1) for name in node.get("required", [])}
    if kind == "array":
        return [_build(node.get("items", {}), defs, depth=depth + 1) for _ in range(int(node.get("minItems", 0)))]
    if kind == "string":
        return _string(node)
    if kind == "integer":
        return int(node.get("minimum", node.get("exclusiveMinimum", -1) + 1))
    if kind == "number":
        return float(node.get("minimum", node.get("exclusiveMinimum", -1) + 1))
    if kind == "boolean":
        return False
    if kind == "null":
        return None
    return {}


def _string(node: dict[str, Any]) -> str:
    """A string that satisfies the node's pattern, format and length limits."""
    pattern = node.get("pattern")
    if pattern is not None:
        for candidate in _PATTERN_CANDIDATES:
            if re.fullmatch(pattern, candidate):
                return candidate
        raise ValueError(f"no example candidate matches pattern {pattern!r}")
    fmt = node.get("format")
    if fmt == "date-time":
        return "2026-09-14T12:00:00Z"
    if fmt == "date":
        return "2026-09-14"
    if fmt == "uuid":
        return "00000000-0000-4000-8000-000000000000"
    value = "example"
    minimum = int(node.get("minLength", 0))
    if len(value) < minimum:
        value += "x" * (minimum - len(value))
    maximum = node.get("maxLength")
    return value[: int(maximum)] if maximum is not None else value


def example_framework(framework_id: str = "example-framework") -> "CompetencyFramework":
    """A small framework with everything a real one has, for tests.

    Two domains — one live, one not — four scored competencies with descriptors
    on every point of the scale, a free-text section, and the marking prompt.
    Nothing exam-shaped: the platform ships no frameworks, so a test that needs
    one builds it here rather than reaching for a catalogue.
    """
    from ..contracts.framework import Competency, CompetencyDomain, CompetencyFramework

    def scored() -> dict[str, Any]:
        """The schema for one scored competency: a score, a supporting phrase and an explanation."""
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["score", "supporting_phrase", "score_explanation"],
            "properties": {
                "score": {"type": "string", "enum": ["R", "A", "G"]},
                "supporting_phrase": {"type": "string"},
                "score_explanation": {"type": "string"},
            },
        }

    descriptors = {"G": "Does all of it.", "A": "Misses one part.", "R": "Misses most of it."}
    return CompetencyFramework(
        id=framework_id,
        label="Example framework",
        version="1",
        domains=(
            CompetencyDomain(id="gathering", label="Gathering information", live=True),
            CompetencyDomain(id="wrap_up", label="Closing the consultation", live=False),
        ),
        competencies=(
            Competency(id="opens_well", label="Opens well", domain_id="gathering", descriptors=descriptors),
            Competency(id="asks_openly", label="Asks open questions", domain_id="gathering", descriptors=descriptors),
            Competency(id="explains", label="Explains clearly", domain_id="wrap_up", descriptors=descriptors),
            Competency(id="safety_nets", label="Safety nets", domain_id="wrap_up", descriptors=descriptors),
        ),
        scale=("R", "A", "G"),
        system_prompt="You are marking a consultation. Fill every field of the schema.",
        result_schema={
            "type": "object",
            "title": "ExampleResult",
            "additionalProperties": False,
            "required": ["gathering", "wrap_up", "overall_comment"],
            "properties": {
                "gathering": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["opens_well", "asks_openly"],
                    "properties": {"opens_well": scored(), "asks_openly": scored()},
                },
                "wrap_up": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["explains", "safety_nets"],
                    "properties": {"explains": scored(), "safety_nets": scored()},
                },
                "overall_comment": {"type": "string"},
            },
        },
    )
