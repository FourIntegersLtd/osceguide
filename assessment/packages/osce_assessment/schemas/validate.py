"""A small JSON Schema checker for the subset the marking schemas use.

Returns human-readable problems rather than raising, so the evaluator can
attach them to its error. Covers the keywords the platform schemas contain:
type, properties/required/additionalProperties, items, enum, const, anyOf,
$ref/$defs, and string pattern/minLength/maxLength.
"""

from __future__ import annotations

import re
from typing import Any

from .strict import resolve_ref

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate_against_schema(payload: Any, schema: dict[str, Any]) -> list[str]:
    """Check a payload against a schema and return every problem found; empty means valid."""
    problems: list[str] = []
    _check(payload, schema, root=schema, path="$", problems=problems, depth=0)
    return problems


def _check(value: Any, node: dict[str, Any], *, root: dict[str, Any], path: str, problems: list[str], depth: int) -> None:
    """Check one value against one schema node, recursing into children and appending problems."""
    if depth > 64:
        problems.append(f"{path}: schema nesting too deep")
        return
    if "$ref" in node:
        merged = {**resolve_ref(root, node["$ref"]), **{key: value for key, value in node.items() if key != "$ref"}}
        _check(value, merged, root=root, path=path, problems=problems, depth=depth + 1)
        return
    if "const" in node and value != node["const"]:
        problems.append(f"{path}: expected constant {node['const']!r}")
        return
    if "enum" in node and value not in node["enum"]:
        problems.append(f"{path}: {value!r} is not one of {node['enum']!r}")
        return
    if "anyOf" in node:
        for option in node["anyOf"]:
            trial: list[str] = []
            _check(value, option, root=root, path=path, problems=trial, depth=depth + 1)
            if not trial:
                return
        problems.append(f"{path}: matches none of the allowed alternatives")
        return

    kind = node.get("type")
    kinds = kind if isinstance(kind, list) else ([kind] if kind else [])
    if kinds and not any(_TYPE_CHECKS.get(type_name, lambda candidate: True)(value) for type_name in kinds):
        problems.append(f"{path}: expected {'/'.join(kinds)}, got {type(value).__name__}")
        return

    if isinstance(value, dict) and ("properties" in node or node.get("type") == "object"):
        properties = node.get("properties", {})
        for name in node.get("required", []):
            if name not in value:
                problems.append(f"{path}.{name}: required")
        for name, sub in properties.items():
            if name in value:
                _check(value[name], sub, root=root, path=f"{path}.{name}", problems=problems, depth=depth + 1)
        if node.get("additionalProperties") is False:
            for extra in sorted(set(value) - set(properties)):
                problems.append(f"{path}.{extra}: not permitted")
    elif isinstance(value, list) and "items" in node:
        for index, item in enumerate(value):
            _check(item, node["items"], root=root, path=f"{path}[{index}]", problems=problems, depth=depth + 1)
    elif isinstance(value, str):
        pattern = node.get("pattern")
        if pattern and not re.search(pattern, value):
            problems.append(f"{path}: {value!r} does not match {pattern!r}")
        if "minLength" in node and len(value) < node["minLength"]:
            problems.append(f"{path}: shorter than {node['minLength']}")
        if "maxLength" in node and len(value) > node["maxLength"]:
            problems.append(f"{path}: longer than {node['maxLength']}")
