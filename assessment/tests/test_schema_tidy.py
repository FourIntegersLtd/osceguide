"""Model noise is removed from a marking before it is stored (2026-10-03 train walk)."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from types import SimpleNamespace

from osce_assessment.contracts import (
    AIInteractionProfile,
    AssessmentAttempt,
    AssessmentDefinition,
    EvaluationPolicy,
    InteractionMode,
    Scenario,
    ScenarioRef,
    ScenarioSource,
    Transcript,
)
from osce_assessment.evaluation import LLMEvaluator
from osce_assessment.schemas.tidy import tidy_against_schema
from osce_assessment.schemas.validate import validate_against_schema
from osce_assessment.testing import StaticFrameworkProvider, example_framework, example_payload_for

_STRINGS = {"type": "array", "items": {"type": "string"}}

# The shape of an SCA rubric's "Actionable feedback" section, as the schema builder derives it.
ACTIONABLE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tasks_feedback", "overall_priorities", "cultural_linguistic_considerations", "language_adaptations"],
    "properties": {
        "tasks_feedback": {"$ref": "#/$defs/DomainFeedback"},
        "overall_priorities": {"type": "array", "items": {"$ref": "#/$defs/Priority"}},
        "cultural_linguistic_considerations": _STRINGS,
        "language_adaptations": {"anyOf": [_STRINGS, {"type": "null"}]},
    },
}
DEFS = {
    "DomainFeedback": {
        "type": "object",
        "additionalProperties": False,
        "required": ["score", "strengths"],
        "properties": {
            "score": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}, "minItems": 2},
        },
    },
    "Priority": {
        "type": "object",
        "additionalProperties": False,
        "required": ["area", "improvement_steps"],
        "properties": {"area": {"type": "string"}, "improvement_steps": _STRINGS},
    },
}
PSA = {"area": "Clarify PSA value and next steps", "improvement_steps": ["State the value", "Book the review"]}


def _schema() -> dict:
    return {"type": "object", "properties": {"actionable_feedback": ACTIONABLE}, "$defs": DEFS}


def test_a_field_name_written_as_an_item_and_a_repeated_priority_are_removed() -> None:
    noisy = {
        "actionable_feedback": {
            "tasks_feedback": {"score": "A", "strengths": ["Opened well", "Summarised"]},
            "overall_priorities": [PSA, copy.deepcopy(PSA), {"area": "Safety net", "improvement_steps": ["Say when"]}],
            "cultural_linguistic_considerations": ["Checked understanding", "language_adaptations"],
            "language_adaptations": ["Avoid 'PSA' without explaining it", " avoid 'psa'  without explaining it"],
        }
    }

    tidied = tidy_against_schema(noisy, _schema())

    assert tidied == {
        "actionable_feedback": {
            "tasks_feedback": {"score": "A", "strengths": ["Opened well", "Summarised"]},
            "overall_priorities": [PSA, {"area": "Safety net", "improvement_steps": ["Say when"]}],
            "cultural_linguistic_considerations": ["Checked understanding"],
            "language_adaptations": ["Avoid 'PSA' without explaining it"],
        }
    }
    assert noisy["actionable_feedback"]["overall_priorities"][1] == PSA  # the input is not mutated


def test_a_list_is_never_shortened_below_its_minimum() -> None:
    payload = {"actionable_feedback": {"tasks_feedback": {"score": "A", "strengths": ["Same", "same"]}}}

    tidied = tidy_against_schema(payload, _schema())

    assert tidied["actionable_feedback"]["tasks_feedback"]["strengths"] == ["Same", "same"]


class _Primary:
    """A primary provider that answers with a fixed payload."""

    def __init__(self, payload: dict) -> None:
        content = json.dumps(payload)
        message = SimpleNamespace(content=content, refusal=None)
        create = lambda **_: SimpleNamespace(choices=[SimpleNamespace(message=message)])  # noqa: E731
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_the_evaluator_stores_the_tidied_marking() -> None:
    base = example_framework()
    schema = copy.deepcopy(base.result_schema)
    schema["properties"]["actionable_feedback"] = ACTIONABLE
    schema["$defs"] = DEFS
    framework = base.model_copy(update={"result_schema": schema})
    payload = example_payload_for(base.result_schema)
    payload["actionable_feedback"] = {
        "tasks_feedback": {"score": "A", "strengths": ["Opened well", "Summarised"]},
        "overall_priorities": [PSA, PSA],
        "cultural_linguistic_considerations": ["language_adaptations"],
        "language_adaptations": None,
    }
    policy = EvaluationPolicy(framework_id=framework.id, openai_model="m", system_prompt_override="Mark it.", version="v1")
    definition = AssessmentDefinition(
        id="v1",
        version="v1",
        framework_id=framework.id,
        scenario_ref=ScenarioRef(source=ScenarioSource.INLINE, scenario_id="s"),
        interaction_profile=AIInteractionProfile(mode=InteractionMode.PATIENT),
        evaluation_policy=policy,
        snapshot_at=datetime.now(timezone.utc),
    )
    attempt = AssessmentAttempt(attempt_id="a1", definition=definition, candidate_ref="")
    evaluator = LLMEvaluator(
        framework_provider=StaticFrameworkProvider(framework), primary_client=lambda: _Primary(payload)
    )

    result = evaluator.evaluate(
        attempt,
        Transcript(attempt_id="a1", messages=(), complete=True),
        policy,
        Scenario(id="s", source=ScenarioSource.INLINE, title="Station"),
    )

    assert result.result["actionable_feedback"]["overall_priorities"] == [PSA]
    assert result.result["actionable_feedback"]["cultural_linguistic_considerations"] == []
    assert result.result["gathering"] == payload["gathering"]  # the marks themselves are untouched
    assert validate_against_schema(result.result, schema) == []
