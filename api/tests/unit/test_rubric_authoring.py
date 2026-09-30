"""The builder's pure helpers: the sample result, draft instructions and a pasted transcript.

The sample is checked against the schema a marker is actually constrained by,
for every rubric the platform seeds, so a preview never shows feedback for a
result no model could have written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.features.attempts.errors import TrialTranscriptInvalid
from app.features.attempts.service_trial import parse_transcript
from app.features.rubrics import authoring, domain
from app.features.rubrics.service_authoring import preview

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / "seeds" / "platform-starter.json").read_text())
PROFILES = ROOT / "app" / "features" / "rubrics" / "profiles"


def schema_problems(schema: dict[str, Any], value: Any, path: str = "$") -> list[str]:
    """Where `value` breaks `schema`, for the subset of JSON Schema the builder writes.

    No `jsonschema` is installed, so this walks what `schema_builder` uses:
    type, enum, minimum, maximum, minItems, required, additionalProperties, anyOf.
    """
    if "anyOf" in schema:
        if any(not schema_problems(option, value, path) for option in schema["anyOf"]):
            return []
        return [f"{path}: matches no anyOf option"]
    expected = schema.get("type")
    type_checks = {
        "object": lambda candidate: isinstance(candidate, dict),
        "array": lambda candidate: isinstance(candidate, list),
        "string": lambda candidate: isinstance(candidate, str),
        "boolean": lambda candidate: isinstance(candidate, bool),
        "integer": lambda candidate: isinstance(candidate, int) and not isinstance(candidate, bool),
        "number": lambda candidate: isinstance(candidate, int | float) and not isinstance(candidate, bool),
        "null": lambda candidate: candidate is None,
    }
    if expected and not type_checks[expected](value):
        return [f"{path}: expected {expected}, got {value!r}"]
    problems: list[str] = []
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} not in {schema['enum']}")
    if "minimum" in schema and value < schema["minimum"]:
        problems.append(f"{path}: below minimum")
    if "maximum" in schema and value > schema["maximum"]:
        problems.append(f"{path}: above maximum")
    if expected == "array":
        if len(value) < schema.get("minItems", 0):
            problems.append(f"{path}: fewer than minItems")
        for index, item in enumerate(value):
            problems += schema_problems(schema["items"], item, f"{path}[{index}]")
    if expected == "object":
        properties = schema.get("properties", {})
        problems += [f"{path}.{key}: required" for key in schema.get("required", []) if key not in value]
        if schema.get("additionalProperties") is False:
            problems += [f"{path}.{key}: not allowed" for key in value if key not in properties]
        for key, item in value.items():
            if key in properties:
                problems += schema_problems(properties[key], item, f"{path}.{key}")
    return problems


@pytest.mark.parametrize("exam", SEED["exams"], ids=lambda exam: exam["code"])
def test_the_sample_result_is_one_the_marker_schema_accepts(exam: dict[str, Any]) -> None:
    structure = domain.parse_structure(exam["rubric"]["structure"])

    sample = authoring.sample_result(structure)

    assert schema_problems(domain.derive_result_schema(structure), sample) == []


@pytest.mark.parametrize("exam", SEED["exams"], ids=lambda exam: exam["code"])
def test_profile_of_reads_what_the_generator_wrote(exam: dict[str, Any]) -> None:
    written = json.loads((PROFILES / f"{exam['code']}.json").read_text())

    assert authoring.profile_of(exam["rubric"]["structure"]) == written


def test_a_blank_rubric_previews_one_green_competency() -> None:
    previewed = preview(authoring.blank_structure())

    assert previewed.valid is True
    assert previewed.sample_result == {
        "domain_1": {
            "competency_1": {
                "score": "G",
                "evidence": "Sample evidence for Competency 1.",
                "explanation": "Sample explanation for Competency 1.",
            }
        }
    }
    assert previewed.sample_totals is not None
    assert previewed.sample_totals.domains[0].counts == {"G": 1, "A": 0, "R": 0}
    assert previewed.result_schema["required"] == ["domain_1"]


def test_an_invalid_draft_previews_as_its_problems() -> None:
    structure = authoring.blank_structure()
    structure["sections"][0]["competencies"] = []

    previewed = preview(structure)

    assert previewed.valid is False
    assert [problem.model_dump() for problem in previewed.problems] == [
        {"path": "sections[0].competencies", "message": "A domain needs at least one competency to rate."}
    ]
    assert previewed.sample_result is None


def test_draft_instructions_prefer_the_source_wording_then_the_role() -> None:
    structure = authoring.blank_structure()

    drafts = authoring.draft_instructions(
        structure,
        {"domain_1.competency_1": "Greets the patient."},
        {"domain": "D.", "rating": "R.", "evidence": "E."},
    )

    assert [(slot.path, slot.key, text, source) for slot, text, source in drafts] == [
        ("sections[0]", "domain_1", "D.", "generic"),
        ("sections[0].competencies[0]", "domain_1.competency_1", "Greets the patient.", "rubric"),
        ("sections[0].competencyFields[0]", "domain_1.*.score", "R.", "generic"),
        ("sections[0].competencyFields[1]", "domain_1.*.evidence", "E.", "generic"),
    ]


def test_a_pasted_transcript_becomes_ordered_turns() -> None:
    turns = parse_transcript(
        "Doctor: Hello, what brings you in?\nPatient: Chest pain\nsince this morning.\n\n"
        "Dr Patel: Where is it?"
    )

    assert turns == [
        {"role": "candidate", "message": "Hello, what brings you in?", "seq": 0},
        {"role": "patient", "message": "Chest pain since this morning.", "seq": 1},
        {"role": "candidate", "message": "Where is it?", "seq": 2},
    ]


@pytest.mark.parametrize(
    "text",
    ["no speaker on the first line", "Patient: I only talk to myself."],
    ids=["no speaker", "no candidate"],
)
def test_a_transcript_with_nothing_to_mark_is_refused(text: str) -> None:
    with pytest.raises(TrialTranscriptInvalid):
        parse_transcript(text)
