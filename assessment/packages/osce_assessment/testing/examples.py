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
    while "$ref" in node:
        node = defs[node["$ref"].rsplit("/", 1)[-1]]
    return node


def _build(node: dict[str, Any], defs: dict[str, Any], *, depth: int) -> Any:
    if depth > _MAX_DEPTH:
        raise RecursionError("schema nesting exceeds the example generator's limit")
    node = _resolve(node, defs)
    if "const" in node:
        return node["const"]
    if "enum" in node:
        return node["enum"][0]
    for combinator in ("anyOf", "oneOf"):
        if combinator in node:
            options = [_resolve(o, defs) for o in node[combinator]]
            preferred = [o for o in options if o.get("type") != "null"] or options
            return _build(preferred[0], defs, depth=depth + 1)
    if "allOf" in node:
        merged: dict[str, Any] = {}
        for part in node["allOf"]:
            merged.update(_resolve(part, defs))
        return _build(merged, defs, depth=depth + 1)
    kind = node.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), kind[0])
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
