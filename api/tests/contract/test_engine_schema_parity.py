"""Oracle: `b2b-api/tests/test_engine_schema_parity.py`.

The legacy test kept the engine's *data* schemas from drifting away from the
live pydantic classes the two backends marked with, while the evaluator was
mid-move from one to the other. That move is finished here — this platform has
no per-exam marking classes at all, the engine owns the shape — so the half of
the oracle that compared class to data has nothing left to compare.

What survives is the half that still bites, and it is the one worth keeping:

  * **The strict transform.** OpenAI structured output refuses a schema unless
    every object forbids additional properties and lists every property as
    required. The engine does that transform itself. In b2b the OpenAI SDK's
    own `to_strict_json_schema` was the oracle — what the SDK would send for
    the class, the engine must send for the data. The SDK is not a dependency
    here, so the assertions below state what it *does*, applied to the schemas
    production actually marks against (`tests/fixtures/legacy_schemas/`).
  * **Nothing may be dropped.** A transform that silently loses a field leaves
    the model never asked to fill it, and a candidate unmarked on a domain with
    no error anywhere.

Skips rather than fails while the engine is absent or being reworked, exactly
as the legacy test did — `poetry install` puts it in place.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

strict = pytest.importorskip(
    "osce_assessment.schemas.strict",
    reason="the osce_assessment engine is not installed; run `poetry install`",
)

SCHEMAS = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_schemas"
EXAMS = ["sca", "casc", "plab", "ortho"]


def marking_schema(exam: str) -> dict[str, Any]:
    """The exam-arm snapshot: the base model, without b2c's storage metadata."""
    return json.loads((SCHEMAS / "b2b" / f"{exam}.json").read_text(encoding="utf-8"))


def objects_in(schema: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every object node in the schema, by path. `$defs` included."""
    found: list[tuple[str, dict[str, Any]]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                found.append((path or "/", node))
            for key, value in node.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(schema, "")
    return found


def property_paths(schema: dict[str, Any]) -> set[str]:
    return {f"{path}:{name}" for path, node in objects_in(schema) for name in node["properties"]}


@pytest.mark.parametrize("exam", EXAMS)
def test_every_object_forbids_additional_properties(exam: str) -> None:
    """What structured output refuses a schema for, first."""
    transformed = strict.to_strict_json_schema(marking_schema(exam))
    loose = [path for path, node in objects_in(transformed) if node.get("additionalProperties") is not False]
    assert not loose, f"{exam}: objects that still allow extra properties: {loose}"


@pytest.mark.parametrize("exam", EXAMS)
def test_every_property_is_required(exam: str) -> None:
    """Structured output has no notion of optional: absent means refused.

    An optional field is expressed as a nullable one, so the model is always
    asked and may answer "nothing" — rather than the request being rejected.
    """
    transformed = strict.to_strict_json_schema(marking_schema(exam))
    incomplete = [
        path
        for path, node in objects_in(transformed)
        if sorted(node.get("required", [])) != sorted(node["properties"])
    ]
    assert not incomplete, f"{exam}: objects whose required list is not every property: {incomplete}"


@pytest.mark.parametrize("exam", EXAMS)
def test_the_transform_drops_no_marking_field(exam: str) -> None:
    """The failure this exists for.

    A transform that loses a property leaves the model never asked to fill it,
    and a candidate unmarked on a domain, with nothing anywhere reporting an
    error — the schema is still valid, it is just smaller than the rubric.
    """
    original = marking_schema(exam)
    transformed = strict.to_strict_json_schema(original)
    missing = property_paths(original) - property_paths(transformed)
    assert not missing, f"{exam}: the strict transform dropped {sorted(missing)}"


@pytest.mark.parametrize("exam", EXAMS)
def test_the_transform_is_idempotent(exam: str) -> None:
    """Applying it twice is applying it once.

    Not pedantry: the schema is transformed on the way into a marking call, and
    a rubric that has already been stored strict must not come out different.
    """
    once = strict.to_strict_json_schema(marking_schema(exam))
    twice = strict.to_strict_json_schema(json.loads(json.dumps(once)))
    assert once == twice


@pytest.mark.parametrize("exam", EXAMS)
def test_the_transform_leaves_a_schema_that_still_describes_the_same_exam(exam: str) -> None:
    """A sanity check with teeth: the titles and descriptions survive.

    They are what tells the marking model what it is looking at, and a
    transform concerned only with structure is exactly the kind of code that
    would discard them.
    """
    original = marking_schema(exam)
    transformed = strict.to_strict_json_schema(original)
    assert transformed.get("title") == original.get("title")
    assert transformed.get("description") == original.get("description")
