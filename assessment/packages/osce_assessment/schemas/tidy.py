"""Remove two kinds of model noise from a filled payload before it is stored.

Strict structured output fixes a payload's shape, not what goes in its
strings. Two slips reached candidates' feedback on 2026-10-03:

- **A key written as a value.** A list of strings holding the bare name of a
  field beside it (``"language_adaptations"`` as an item of
  ``cultural_linguistic_considerations``): the model announcing the next
  field inside the current one. Shown as a stray line of snake_case.
- **The same item twice.** One priority area ("Clarify PSA value and next
  steps") listed twice in the same list.

Both are removed by walking the schema, so nothing here knows an exam or a
field name. A list is never shortened below its ``minItems``, so tidying can
never turn a valid payload into one the validator refuses; scores live in
object properties, not lists, and are never touched.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from .strict import resolve_ref

_MAX_DEPTH = 64


def tidy_against_schema(payload: Any, schema: dict[str, Any]) -> Any:
    """A copy of ``payload`` without leaked field names or repeated list items."""
    return _tidy(copy.deepcopy(payload), schema, root=schema, siblings=frozenset(), depth=0)


def _resolve(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """The node with its ``$ref`` (if any) merged in, sibling keys winning."""
    ref = node.get("$ref")
    if not ref:
        return node
    return {**resolve_ref(root, ref), **{key: value for key, value in node.items() if key != "$ref"}}


def _identity(item: Any) -> str:
    """What makes two list items "the same": case and spacing ignored for text."""
    if isinstance(item, str):
        return " ".join(item.split()).casefold()
    return json.dumps(item, sort_keys=True, default=str)


def _tidy(value: Any, node: dict[str, Any], *, root: dict[str, Any], siblings: frozenset[str], depth: int) -> Any:
    """Tidy one value against one schema node; ``siblings`` are the field names around it."""
    if depth > _MAX_DEPTH or not isinstance(node, dict):
        return value
    node = _resolve(node, root)

    if "anyOf" in node:
        # The first option whose type fits; a `null` alternative has nothing to tidy.
        for option in node["anyOf"]:
            resolved = _resolve(option, root)
            if (isinstance(value, dict) and resolved.get("type") == "object") or (
                isinstance(value, list) and resolved.get("type") == "array"
            ):
                return _tidy(value, resolved, root=root, siblings=siblings, depth=depth + 1)
        return value

    if isinstance(value, dict):
        properties = node.get("properties")
        if not isinstance(properties, dict):
            return value
        names = frozenset(properties)
        for name, sub in properties.items():
            if name in value:
                value[name] = _tidy(value[name], sub, root=root, siblings=names, depth=depth + 1)
        return value

    if isinstance(value, list):
        items = node.get("items")
        if isinstance(items, dict):
            value = [_tidy(item, items, root=root, siblings=frozenset(), depth=depth + 1) for item in value]
        return _without_noise(value, siblings=siblings, min_items=int(node.get("minItems") or 0))

    return value


def _without_noise(items: list[Any], *, siblings: frozenset[str], min_items: int) -> list[Any]:
    """Drop leaked field names and repeats, unless that would leave fewer than ``min_items``."""
    leaked = {name.casefold() for name in siblings}
    seen: set[str] = set()
    kept: list[Any] = []
    for item in items:
        if isinstance(item, str) and item.strip().casefold() in leaked:
            continue
        identity = _identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        kept.append(item)
    return kept if len(kept) >= min_items else items
