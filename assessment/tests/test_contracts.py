"""Contract models: serialisation, immutability, and the opaque attempt context."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from osce_assessment.contracts import (
    AIInteractionProfile,
    AssessmentAttempt,
    AssessmentDefinition,
    AssessmentResult,
    AttemptStatus,
    EvaluationPolicy,
    InteractionMode,
    MessageRole,
    RuntimeHint,
    Scenario,
    ScenarioRef,
    ScenarioSource,
    Transcript,
    TranscriptMessage,
)

FIXED_TIME = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def test_definition_round_trips_through_json(definition: AssessmentDefinition) -> None:
    restored = AssessmentDefinition.model_validate_json(definition.model_dump_json())
    assert restored == definition


def test_attempt_round_trips_with_its_definition_snapshot(attempt: AssessmentAttempt) -> None:
    restored = AssessmentAttempt.model_validate_json(attempt.model_dump_json())
    assert restored == attempt
    assert restored.definition.version == "3"


def test_definition_is_frozen(definition: AssessmentDefinition) -> None:
    with pytest.raises(ValidationError):
        definition.version = "4"  # type: ignore[misc]


def test_attempt_status_advances_by_copy(attempt: AssessmentAttempt) -> None:
    running = attempt.model_copy(update={"status": AttemptStatus.RUNNING})
    assert attempt.status is AttemptStatus.CREATED
    assert running.status is AttemptStatus.RUNNING


def test_attempt_context_is_opaque_and_survives_round_trip() -> None:
    """Any string keys the consumer wants back must pass through untouched."""
    context = {
        "whatever_the_consumer_calls_it": "value-1",
        "another-correlation-id": "value-2",
    }
    attempt = AssessmentAttempt(
        attempt_id="a",
        definition=_minimal_definition(),
        candidate_ref="candidate",
        attempt_context=context,
    )
    assert AssessmentAttempt.model_validate_json(attempt.model_dump_json()).attempt_context == context


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ScenarioRef(source=ScenarioSource.LIBRARY, scenario_id="s", extra="nope")  # type: ignore[call-arg]


def test_scenario_requires_non_negative_duration() -> None:
    with pytest.raises(ValidationError):
        Scenario(id="s", source=ScenarioSource.LIBRARY, title="t", duration_seconds=-1)


def test_profile_defaults_to_the_pipeline_runtime() -> None:
    profile = AIInteractionProfile(mode=InteractionMode.PATIENT)
    assert profile.runtime_hint is RuntimeHint.PIPELINE
    assert profile.instructions == ""
    assert profile.tools == ()


def test_policy_keeps_model_choice_as_data() -> None:
    """Two consumers differ by policy, not by engine branch."""
    framework_id = "sca-rcgp-v1"
    b2c = EvaluationPolicy(
        framework_id=framework_id, primary_model="gpt-5-mini", primary_reasoning_effort="low"
    )
    b2b = EvaluationPolicy(
        framework_id=framework_id, primary_model="gpt-4o", system_prompt_override="b2b wording"
    )
    assert b2c.framework_id == b2b.framework_id
    assert (b2c.primary_model, b2c.primary_reasoning_effort) == ("gpt-5-mini", "low")
    assert (b2b.primary_model, b2b.primary_reasoning_effort) == ("gpt-4o", None)
    assert b2c.timeout_s == b2b.timeout_s == 480


def test_policy_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValidationError):
        EvaluationPolicy(framework_id="f", primary_model="m", timeout_s=0)


def test_transcript_message_seq_must_not_be_negative() -> None:
    with pytest.raises(ValidationError):
        TranscriptMessage(
            role=MessageRole.USER,
            message="hello",
            timestamp=FIXED_TIME,
            message_id="m",
            seq=-1,
        )


def test_transcript_defaults_to_incomplete_and_empty() -> None:
    transcript = Transcript(attempt_id="a")
    assert transcript.messages == ()
    assert transcript.complete is False


def test_result_carries_the_policy_version_it_was_scored_under() -> None:
    result = AssessmentResult(
        attempt_id="a",
        framework_id="sca-rcgp-v1",
        policy_version="policy-7",
        result={"overall": "competent"},
        provider="openai",
        model="gpt-4o",
        generated_at=FIXED_TIME,
    )
    assert AssessmentResult.model_validate_json(result.model_dump_json()) == result
    assert result.policy_version == "policy-7"


def _minimal_definition() -> AssessmentDefinition:
    return AssessmentDefinition(
        id="d",
        version="1",
        framework_id="sca-rcgp-v1",
        scenario_ref=ScenarioRef(source=ScenarioSource.LIBRARY, scenario_id="s"),
        interaction_profile=AIInteractionProfile(mode=InteractionMode.PATIENT),
        evaluation_policy=EvaluationPolicy(framework_id="sca-rcgp-v1", primary_model="m"),
        snapshot_at=FIXED_TIME,
    )
