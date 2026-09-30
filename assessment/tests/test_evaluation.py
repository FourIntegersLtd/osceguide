"""The shared evaluator: one scoring path, provider calls pinned, no vendor SDK."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from osce_assessment.contracts import (
    CompetencyFramework,
    EvaluationPolicy,
    MessageRole,
    Scenario,
    ScenarioSource,
    Transcript,
    TranscriptMessage,
)
from osce_assessment.evaluation import EvaluationError, LLMEvaluator, render_transcript_for_marking
from osce_assessment.prompts import prompt_text, system_prompt
from osce_assessment.schemas.strict import to_strict_json_schema
from osce_assessment.testing import StaticFrameworkProvider, example_framework, example_payload_for

FIXED = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)

AUTHORED = example_framework()

SIMPLE = CompetencyFramework(
    id="simple-v1",
    label="Simple",
    result_schema={
        "type": "object",
        "properties": {"overall": {"type": "string", "enum": ["R", "A", "G"]}, "comment": {"type": "string"}},
        "required": ["overall", "comment"],
    },
)


def policy(**overrides) -> EvaluationPolicy:
    base = dict(framework_id=SIMPLE.id, primary_model="primary-model", fallback_model="fallback-model", version="p7")
    base.update(overrides)
    return EvaluationPolicy(**base)


def transcript() -> Transcript:
    return Transcript(
        attempt_id="a1",
        complete=True,
        messages=(
            TranscriptMessage(role=MessageRole.ASSISTANT, message="I've had this tightness.", timestamp=FIXED, message_id="m0", seq=0),
            TranscriptMessage(role=MessageRole.USER, message="  When did it start?  ", timestamp=FIXED, message_id="m1", seq=1),
            TranscriptMessage(role=MessageRole.ASSISTANT, message="   ", timestamp=FIXED, message_id="m2", seq=2),
        ),
    )


def scenario(**overrides) -> Scenario:
    base = dict(id="s", source=ScenarioSource.LIBRARY, title="Chest pain")
    base.update(overrides)
    return Scenario(**base)


class FakePrimary:
    """The slice of an OpenAI-style client the evaluator touches."""

    def __init__(self, *, content=None, refusal=None, error=None) -> None:
        self.calls: list[dict] = []
        self._content, self._refusal, self._error = content, refusal, error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        message = SimpleNamespace(content=self._content, refusal=self._refusal)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeFallback:
    """The slice of an Anthropic-style client the evaluator touches."""

    def __init__(self, *, payload=None, error=None, blocks=None) -> None:
        self.calls: list[dict] = []
        self._payload, self._error, self._blocks = payload, error, blocks
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        if self._blocks is not None:
            return SimpleNamespace(content=self._blocks)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="thinking"), SimpleNamespace(type="tool_use", input=self._payload)])


def evaluator(primary=None, fallback=None, frameworks=None) -> LLMEvaluator:
    return LLMEvaluator(
        framework_provider=frameworks or StaticFrameworkProvider(SIMPLE),
        primary_client=lambda: primary,
        fallback_client=(lambda: fallback) if fallback is not None or fallback is None else None,
        clock=lambda: FIXED,
    )


GOOD = {"overall": "G", "comment": "Clear and structured."}
ATTEMPT = SimpleNamespace(attempt_id="a1")


# --- rendering ------------------------------------------------------------------


def test_transcript_renders_as_tagged_blocks_and_skips_blank_turns() -> None:
    assert render_transcript_for_marking(transcript()) == (
        "<PATIENT>\nI've had this tightness.\n</PATIENT>\n\n<DOCTOR>\nWhen did it start?\n</DOCTOR>"
    )


# --- primary path ---------------------------------------------------------------


def test_primary_success_returns_a_result_tied_to_the_policy() -> None:
    primary = FakePrimary(content=json.dumps(GOOD))
    result = evaluator(primary).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="SYS"), scenario())

    assert result.result == GOOD
    assert result.provider == "primary" and result.model == "primary-model"
    assert result.framework_id == "simple-v1" and result.policy_version == "p7"
    assert result.attempt_id == "a1" and result.generated_at == FIXED
    assert result.raw_metadata == {"fallback_used": False, "attempts": [], "framework_version": "1"}


def test_primary_call_shape_is_strict_structured_output() -> None:
    primary = FakePrimary(content=json.dumps(GOOD))
    evaluator(primary).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="SYS", timeout_s=42), scenario())

    kwargs = primary.calls[0]
    assert kwargs["model"] == "primary-model"
    assert kwargs["timeout"] == 42
    assert "reasoning_effort" not in kwargs
    assert kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "simple-v1", "schema": to_strict_json_schema(SIMPLE.result_schema), "strict": True},
    }
    system, user = kwargs["messages"]
    assert system == {"role": "system", "content": "SYS"}
    assert user["role"] == "user"
    assert "Chest pain" in user["content"]
    assert "<DOCTOR>\nWhen did it start?\n</DOCTOR>" in user["content"]


def test_reasoning_effort_is_forwarded_only_when_the_policy_sets_it() -> None:
    primary = FakePrimary(content=json.dumps(GOOD))
    evaluator(primary).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S", primary_reasoning_effort="low"), scenario())
    assert primary.calls[0]["reasoning_effort"] == "low"


def test_the_system_prompt_comes_from_the_framework_when_not_overridden() -> None:
    """The rubric's author wrote the marking instructions; nothing is chosen by id."""
    primary = FakePrimary(content=json.dumps(example_payload_for(AUTHORED.result_schema)))
    evaluator(primary, frameworks=StaticFrameworkProvider(AUTHORED)).evaluate(
        ATTEMPT, transcript(), policy(framework_id=AUTHORED.id), scenario()
    )
    assert primary.calls[0]["messages"][0]["content"] == AUTHORED.system_prompt


def test_user_prompt_is_the_platform_template_plus_examiner_context() -> None:
    primary = FakePrimary(content=json.dumps(GOOD))
    evaluator(primary).evaluate(
        ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario(examiner_context="\n\n=== EXPECTED ANSWERS ===\nQ1")
    )
    user = primary.calls[0]["messages"][1]["content"]
    expected_prefix = prompt_text("feedback_evaluation_v1").format(
        station_name="Chest pain", transcript=render_transcript_for_marking(transcript())
    )
    assert user == expected_prefix + "\n\n=== EXPECTED ANSWERS ===\nQ1"


def test_an_authored_schema_round_trips_through_the_primary_path() -> None:
    payload = example_payload_for(AUTHORED.result_schema)
    primary = FakePrimary(content=json.dumps(payload))
    result = evaluator(primary, frameworks=StaticFrameworkProvider(AUTHORED)).evaluate(
        ATTEMPT, transcript(), policy(framework_id=AUTHORED.id), scenario()
    )
    assert result.result == payload
    assert primary.calls[0]["response_format"]["json_schema"]["name"] == AUTHORED.id


# --- fallback path --------------------------------------------------------------


def test_refusal_falls_back_and_records_the_reason() -> None:
    primary = FakePrimary(refusal="content policy")
    fallback = FakeFallback(payload=GOOD)
    result = evaluator(primary, fallback).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())

    assert result.provider == "fallback" and result.model == "fallback-model"
    assert result.raw_metadata["fallback_used"] is True
    assert result.raw_metadata["attempts"] == ["primary primary-model: refused: content policy"]


def test_primary_exception_falls_back_with_a_forced_tool_call() -> None:
    primary = FakePrimary(error=RuntimeError("down"))
    fallback = FakeFallback(payload=GOOD)
    evaluator(primary, fallback).evaluate(
        ATTEMPT, transcript(), policy(system_prompt_override="SYS", fallback_max_tokens=123, fallback_temperature=0.5), scenario()
    )

    kwargs = fallback.calls[0]
    assert kwargs["model"] == "fallback-model"
    assert kwargs["max_tokens"] == 123 and kwargs["temperature"] == 0.5
    assert kwargs["system"] == "SYS"
    assert kwargs["messages"] == [{"role": "user", "content": primary.calls[0]["messages"][1]["content"]}]
    assert kwargs["tool_choice"] == {"type": "tool", "name": "simple-v1"}
    (tool,) = kwargs["tools"]
    assert tool["name"] == "simple-v1"
    assert "$ref" not in json.dumps(tool["input_schema"])


def test_non_object_primary_output_falls_back() -> None:
    primary = FakePrimary(content=json.dumps(["not", "an", "object"]))
    fallback = FakeFallback(payload=GOOD)
    result = evaluator(primary, fallback).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())
    assert result.provider == "fallback"
    assert "not an object" in result.raw_metadata["attempts"][0]


def test_unconfigured_primary_goes_straight_to_fallback() -> None:
    fallback = FakeFallback(payload=GOOD)
    result = evaluator(None, fallback).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())
    assert result.provider == "fallback"
    assert result.raw_metadata["attempts"] == ["primary: not configured"]


# --- failures -------------------------------------------------------------------


def test_both_providers_failing_raises_with_both_reasons() -> None:
    primary = FakePrimary(error=RuntimeError("openai down"))
    fallback = FakeFallback(error=RuntimeError("anthropic down"))
    with pytest.raises(EvaluationError) as excinfo:
        evaluator(primary, fallback).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())
    assert excinfo.value.attempts == ["primary primary-model: openai down", "fallback fallback-model: anthropic down"]
    assert "openai down" in str(excinfo.value) and "anthropic down" in str(excinfo.value)


def test_no_fallback_model_means_no_fallback_attempt() -> None:
    primary = FakePrimary(error=RuntimeError("down"))
    fallback = FakeFallback(payload=GOOD)
    with pytest.raises(EvaluationError) as excinfo:
        evaluator(primary, fallback).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S", fallback_model=None), scenario())
    assert fallback.calls == []
    assert excinfo.value.attempts == ["primary primary-model: down"]


def test_fallback_factory_returning_none_is_reported_as_unconfigured() -> None:
    primary = FakePrimary(error=RuntimeError("down"))
    ev = LLMEvaluator(framework_provider=StaticFrameworkProvider(SIMPLE), primary_client=lambda: primary, fallback_client=lambda: None, clock=lambda: FIXED)
    with pytest.raises(EvaluationError) as excinfo:
        ev.evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())
    assert excinfo.value.attempts == ["primary primary-model: down", "fallback: not configured"]


def test_a_result_that_breaks_the_schema_is_rejected_not_stored() -> None:
    primary = FakePrimary(content=json.dumps({"overall": "excellent", "comment": "x", "likes": 0}))
    with pytest.raises(EvaluationError, match="does not match the simple-v1 schema") as excinfo:
        evaluator(primary).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())
    assert "$.overall" in str(excinfo.value)


def test_fallback_without_a_tool_use_block_is_an_error() -> None:
    fallback = FakeFallback(blocks=[SimpleNamespace(type="text", text="sorry")])
    with pytest.raises(EvaluationError) as excinfo:
        evaluator(None, fallback).evaluate(ATTEMPT, transcript(), policy(system_prompt_override="S"), scenario())
    assert "no tool_use block" in excinfo.value.attempts[-1]


def test_framework_without_a_schema_cannot_be_scored() -> None:
    bare = CompetencyFramework(id="bare-v1", label="Bare")
    with pytest.raises(EvaluationError, match="no result schema"):
        evaluator(FakePrimary(content="{}"), frameworks=StaticFrameworkProvider(bare)).evaluate(
            ATTEMPT, transcript(), policy(framework_id="bare-v1", system_prompt_override="S"), scenario()
        )


def test_a_framework_with_no_prompt_and_no_override_is_refused() -> None:
    """There is no default to fall back on: a rubric nobody wrote a prompt for cannot be marked."""
    with pytest.raises(EvaluationError, match="carries no system prompt"):
        evaluator(FakePrimary(content=json.dumps(GOOD))).evaluate(ATTEMPT, transcript(), policy(), scenario())


def test_unknown_framework_id_surfaces_from_the_provider() -> None:
    with pytest.raises(LookupError):
        evaluator(FakePrimary(content="{}")).evaluate(ATTEMPT, transcript(), policy(framework_id="nope"), scenario())


NATIVE = CompetencyFramework(
    id="native-v1",
    label="Native",
    scale=(),
    rating={"kind": "range", "minimum": 0, "maximum": 10, "step": "integer"},
    rating_field="score",
    domains=({"id": "clinical", "label": "Clinical"},),
    competencies=({"id": "clinical.awareness", "label": "Awareness", "domain_id": "clinical"},),
    result_schema={
        "type": "object",
        "properties": {
            "clinical": {
                "type": "object",
                "properties": {
                    "awareness": {
                        "type": "object",
                        "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 10}},
                        "required": ["score"],
                    }
                },
                "required": ["awareness"],
            }
        },
        "required": ["clinical"],
    },
)


def test_a_rating_outside_its_native_range_is_rejected_not_stored() -> None:
    """The schema validator does not hold a model to minimum/maximum; the framework does."""
    primary = FakePrimary(content=json.dumps({"clinical": {"awareness": {"score": 11}}}))
    with pytest.raises(EvaluationError, match="a whole number from 0"):
        evaluator(primary, frameworks=StaticFrameworkProvider(NATIVE)).evaluate(
            ATTEMPT, transcript(), policy(framework_id="native-v1", system_prompt_override="S"), scenario()
        )


def test_a_rating_within_its_native_range_is_accepted() -> None:
    primary = FakePrimary(content=json.dumps({"clinical": {"awareness": {"score": 7}}}))
    result = evaluator(primary, frameworks=StaticFrameworkProvider(NATIVE)).evaluate(
        ATTEMPT, transcript(), policy(framework_id="native-v1", system_prompt_override="S"), scenario()
    )
    assert result.result == {"clinical": {"awareness": {"score": 7}}}
