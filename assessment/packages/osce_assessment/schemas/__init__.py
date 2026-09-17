"""Tools for the result schemas rubric authors write.

The platform used to ship one JSON Schema per exam beside this file. It no
longer ships any: a rubric's shape is derived from the domains and
competencies its author entered, and arrives on the framework. What is left
here is the machinery every schema needs whatever its origin — making it
strict enough for a provider's structured-output mode (:mod:`strict`) and
checking a filled payload against it (:mod:`validate`).
"""

from __future__ import annotations

from .strict import inline_refs, resolve_ref, to_strict_json_schema
from .validate import validate_against_schema

__all__ = [
    "inline_refs",
    "resolve_ref",
    "to_strict_json_schema",
    "validate_against_schema",
]
