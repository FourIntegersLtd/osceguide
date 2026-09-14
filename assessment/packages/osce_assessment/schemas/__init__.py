"""Platform marking schemas as data: one JSON Schema per catalogue framework.

These describe the shape a language model is asked to fill when scoring a
transcript, without any storage metadata (ids, timestamps, evaluator). They
were derived from the models the backends use today and are pinned against
them by the backends' own parity tests, so the class and the data cannot
drift apart while both exist.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources
from typing import Any


class UnknownSchemaError(LookupError):
    """Raised for a framework id with no schema file beside this module."""


@lru_cache(maxsize=None)
def _cached(framework_id: str) -> dict[str, Any]:
    ref = resources.files(__name__).joinpath(f"{framework_id}.json")
    if not ref.is_file():
        raise UnknownSchemaError(f"no schema for {framework_id!r}; known: {available_schema_ids()}")
    return json.loads(ref.read_text(encoding="utf-8"))


def load_schema(framework_id: str) -> dict[str, Any]:
    """A fresh copy of the framework's result schema."""
    return copy.deepcopy(_cached(framework_id))


def available_schema_ids() -> tuple[str, ...]:
    return tuple(sorted(p.name[:-5] for p in resources.files(__name__).iterdir() if p.name.endswith(".json")))
