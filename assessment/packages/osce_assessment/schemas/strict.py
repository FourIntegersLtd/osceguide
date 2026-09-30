"""Shape a JSON Schema for each provider's structured-output mode.

``to_strict_json_schema`` mirrors, step for step, what the OpenAI SDK does to
a pydantic model's schema before sending it in strict mode: every object gets
``additionalProperties: false``, every property becomes required, ``None``
defaults are dropped, and a ``$ref`` that carries sibling keys is inlined.
Reproducing it here keeps the data-schema path identical to the class path
the backends use today, without the engine importing the SDK.

``inline_refs`` dereferences ``$ref``/``$defs`` completely, for providers whose
tool schemas do not accept references.
"""

from __future__ import annotations

import copy
from typing import Any

_NOT_GIVEN = object()
_MAX_DEPTH = 64


def to_strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    root = copy.deepcopy(schema)
    return _ensure_strict(root, root=root, depth=0)


def _ensure_strict(node: Any, *, root: dict[str, Any], depth: int) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise TypeError(f"expected a schema object, got {type(node).__name__}")
    if depth > _MAX_DEPTH:
        raise RecursionError("schema nesting exceeds the strict transform's limit")

    for key in ("$defs", "definitions"):
        defs = node.get(key)
        if isinstance(defs, dict):
            for name, sub in defs.items():
                _ensure_strict(sub, root=root, depth=depth + 1)

    if node.get("type") == "object" and "additionalProperties" not in node:
        node["additionalProperties"] = False

    properties = node.get("properties")
    if isinstance(properties, dict):
        node["required"] = list(properties.keys())
        node["properties"] = {
            key: _ensure_strict(sub, root=root, depth=depth + 1) for key, sub in properties.items()
        }

    items = node.get("items")
    if isinstance(items, dict):
        node["items"] = _ensure_strict(items, root=root, depth=depth + 1)

    any_of = node.get("anyOf")
    if isinstance(any_of, list):
        node["anyOf"] = [_ensure_strict(v, root=root, depth=depth + 1) for v in any_of]

    all_of = node.get("allOf")
    if isinstance(all_of, list):
        if len(all_of) == 1:
            node.update(_ensure_strict(all_of[0], root=root, depth=depth + 1))
            node.pop("allOf")
        else:
            node["allOf"] = [_ensure_strict(v, root=root, depth=depth + 1) for v in all_of]

    if node.get("default", _NOT_GIVEN) is None:
        node.pop("default")

    ref = node.get("$ref")
    if ref and len(node) > 1:
        resolved = resolve_ref(root, ref)
        node.update({**resolved, **node})
        node.pop("$ref")
        return _ensure_strict(node, root=root, depth=depth + 1)

    return node


def resolve_ref(root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref {ref!r}; only local references are supported")
    node: Any = root
    for key in ref[2:].split("/"):
        node = node[key]
    if not isinstance(node, dict):
        raise ValueError(f"$ref {ref!r} does not resolve to a schema object")
    return node


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """A copy of the schema with every ``$ref`` replaced by its target."""
    root = copy.deepcopy(schema)

    def walk(node: Any, depth: int) -> Any:
        if depth > _MAX_DEPTH:
            raise RecursionError("schema nesting exceeds the inlining limit")
        if isinstance(node, dict):
            if "$ref" in node:
                resolved = copy.deepcopy(resolve_ref(root, node["$ref"]))
                merged = {**resolved, **{k: v for k, v in node.items() if k != "$ref"}}
                return walk(merged, depth + 1)
            return {k: walk(v, depth + 1) for k, v in node.items() if k not in ("$defs", "definitions")}
        if isinstance(node, list):
            return [walk(v, depth + 1) for v in node]
        return node

    return walk(root, 0)
