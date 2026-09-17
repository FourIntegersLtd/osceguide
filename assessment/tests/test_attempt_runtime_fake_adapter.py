"""The engine's headline contract, proven without LiveKit or an LLM.

    AssessmentDefinition -> AssessmentAttempt -> AttemptRuntime -> Interaction
    -> Transcript -> EvaluationPolicy -> AssessmentResult
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from conftest import FRAMEWORK
from osce_assessment.contracts import (
    AssessmentAttempt,
    AttemptStatus,
    MessageRole,
    Scenario,
    Transcript,
)
from osce_assessment.runtime import (
    AttemptRuntime,
    FakeInteractionAdapter,
    InteractionFailure,
    RetryPolicy,
)
from osce_assessment.testing import (
    FakeEvaluator,
    InMemoryResultSink,
    InMemoryTranscriptSink,
    SimpleProfileBuilder,
    StaticScenarioProvider,
)

SCRIPT = [
    (MessageRole.ASSISTANT, "I've had this tightness in my chest."),
    (MessageRole.USER, "When did it start?"),
    (MessageRole.ASSISTANT, "Two days ago, after climbing the stairs."),
]


class _Clock:
    """Monotonic fake clock so timestamps are deterministic and ordered."""

    def __init__(self) -> None:
        self._now = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        self._now += timedelta(seconds=1)
        return self._now


def build_runtime(
    scenario: Scenario,
    *,
    adapter: FakeInteractionAdapter,
    sink: InMemoryTranscriptSink | None = None,
    evaluator: FakeEvaluator | None = None,
    results: InMemoryResultSink | None = None,
    retry_policy: RetryPolicy = RetryPolicy.immediate(),
) -> tuple[AttemptRuntime, InMemoryTranscriptSink, FakeEvaluator, InMemoryResultSink, StaticScenarioProvider]:
    sink = sink or InMemoryTranscriptSink()
    evaluator = evaluator or FakeEvaluator()
    results = results or InMemoryResultSink()
    provider = StaticScenarioProvider(scenario)
    runtime = AttemptRuntime(
        scenario_provider=provider,
        profile_builder=SimpleProfileBuilder(),
        adapter=adapter,
        transcript_sink=sink,
        evaluator=evaluator,
        result_sink=results,
        retry_policy=retry_policy,
        clock=_Clock(),
        id_factory=lambda: "msg-id",
        runtime_label="fake",
    )
    return runtime, sink, evaluator, results, provider


def test_definition_to_result_without_livekit(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    adapter = FakeInteractionAdapter(SCRIPT)
    runtime, sink, evaluator, results, provider = build_runtime(scenario, adapter=adapter)

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.ok
    assert outcome.attempt.status is AttemptStatus.EVALUATED
    assert outcome.transcript.complete is True
    assert [m.message for m in outcome.transcript.messages] == [text for _, text in SCRIPT]
    assert outcome.result is not None
    assert outcome.result.framework_id == attempt.definition.framework_id
    assert outcome.result.policy_version == "policy-7"
    assert results.saved[0][0] is outcome.result
    assert len(sink.completed) == 1
    assert provider.calls[0][0] == attempt.definition.scenario_ref


def test_the_policy_on_the_definition_is_what_reaches_the_evaluator(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    runtime, _, evaluator, _, _ = build_runtime(scenario, adapter=FakeInteractionAdapter(SCRIPT))

    asyncio.run(runtime.run(attempt))

    _, transcript, policy, seen_scenario = evaluator.calls[0]
    assert policy is attempt.definition.evaluation_policy
    assert seen_scenario is scenario
    assert policy.primary_model == "primary-model"
    assert len(transcript.messages) == len(SCRIPT)


def test_scenario_and_profile_drive_the_interaction(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    adapter = FakeInteractionAdapter(SCRIPT)
    runtime, _, _, _, _ = build_runtime(scenario, adapter=adapter)

    asyncio.run(runtime.run(attempt))

    assert adapter.greetings == ["Hi doctor."]
    profile = adapter.profiles[0]
    assert scenario.title in profile.instructions
    assert "I've had this tightness in my chest." in profile.instructions
    assert profile.tools == ("search_help_faqs",)
    assert adapter.connect_calls == 1
    assert adapter.disconnect_calls == 1
    assert adapter.connected is False


def test_every_turn_is_streamed_in_order_as_it_happens(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    """Streaming is what makes a mid-session crash recoverable."""
    runtime, sink, _, _, _ = build_runtime(scenario, adapter=FakeInteractionAdapter(SCRIPT))

    asyncio.run(runtime.run(attempt))

    assert [m.seq for _, m in sink.appended] == [0, 1, 2]
    assert [m.role for _, m in sink.appended] == [role for role, _ in SCRIPT]
    assert all(attempt_id == attempt.attempt_id for attempt_id, _ in sink.appended)
    timestamps = [m.timestamp for _, m in sink.appended]
    assert timestamps == sorted(timestamps)


def test_attempt_context_reaches_the_ports_untouched(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    runtime, _, _, results, provider = build_runtime(
        scenario, adapter=FakeInteractionAdapter(SCRIPT)
    )

    asyncio.run(runtime.run(attempt))

    assert provider.calls[0][1] == attempt.attempt_context
    assert results.saved[0][1] == attempt.attempt_context


def test_transcript_is_delivered_once_even_when_teardown_races(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    """Two teardown paths both calling deliver must produce one delivery."""
    runtime, sink, _, _, _ = build_runtime(scenario, adapter=FakeInteractionAdapter(SCRIPT))

    async def run_then_redeliver() -> tuple[bool, bool]:
        outcome = await runtime.run(attempt)
        again_a, again_b = await asyncio.gather(
            runtime.deliver(outcome.transcript), runtime.deliver(outcome.transcript)
        )
        return again_a, again_b

    again_a, again_b = asyncio.run(run_then_redeliver())

    assert (again_a, again_b) == (False, False)
    assert sink.complete_calls == 1
    assert len(sink.completed) == 1


def test_concurrent_first_delivery_still_delivers_once(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    runtime, sink, _, _, _ = build_runtime(scenario, adapter=FakeInteractionAdapter())
    transcript = Transcript(attempt_id=attempt.attempt_id, complete=True)

    async def race() -> list[bool]:
        return list(await asyncio.gather(*(runtime.deliver(transcript) for _ in range(5))))

    delivered = asyncio.run(race())

    assert delivered.count(True) == 1
    assert sink.complete_calls == 1


def test_interaction_failure_still_delivers_the_partial_transcript(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    adapter = FakeInteractionAdapter(SCRIPT, fail_after=2)
    runtime, sink, evaluator, results, _ = build_runtime(scenario, adapter=adapter)

    outcome = asyncio.run(runtime.run(attempt))

    assert not outcome.ok
    assert InteractionFailure.__name__ in (outcome.error or "")
    assert outcome.attempt.status is AttemptStatus.FAILED
    assert [m.seq for m in outcome.transcript.messages] == [0, 1]
    assert outcome.transcript.complete is False
    assert outcome.delivered is True
    assert len(sink.completed) == 1
    assert adapter.disconnect_calls == 1
    assert evaluator.calls == []
    assert results.saved == []


def test_delivery_retries_then_succeeds(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    sink = InMemoryTranscriptSink(fail_complete_times=2)
    runtime, _, _, _, _ = build_runtime(
        scenario,
        adapter=FakeInteractionAdapter(SCRIPT),
        sink=sink,
        retry_policy=RetryPolicy.immediate(attempts=3),
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.ok
    assert sink.complete_calls == 3
    assert len(sink.completed) == 1


def test_delivery_failure_fails_the_attempt_and_skips_evaluation(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    sink = InMemoryTranscriptSink(fail_complete_times=99)
    runtime, _, evaluator, results, _ = build_runtime(
        scenario,
        adapter=FakeInteractionAdapter(SCRIPT),
        sink=sink,
        retry_policy=RetryPolicy.immediate(attempts=2),
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.attempt.status is AttemptStatus.FAILED
    assert "delivery failed" in (outcome.error or "")
    assert sink.complete_calls == 2
    assert evaluator.calls == []
    assert results.saved == []


def test_a_failing_append_never_stops_the_interaction(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    """Chunk streaming is best-effort; the session must still finish and score."""
    sink = InMemoryTranscriptSink(fail_append=True)
    runtime, _, _, results, _ = build_runtime(
        scenario, adapter=FakeInteractionAdapter(SCRIPT), sink=sink
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.ok
    assert sink.appended == []
    assert len(outcome.transcript.messages) == len(SCRIPT)
    assert len(results.saved) == 1


def test_empty_transcript_is_not_sent_for_evaluation(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    runtime, sink, evaluator, results, _ = build_runtime(
        scenario, adapter=FakeInteractionAdapter()
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.error == "empty_transcript"
    assert outcome.attempt.status is AttemptStatus.INTERACTION_COMPLETE
    assert len(sink.completed) == 1
    assert evaluator.calls == []
    assert results.saved == []


def test_evaluator_failure_is_reported_without_losing_the_transcript(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    runtime, sink, _, results, _ = build_runtime(
        scenario, adapter=FakeInteractionAdapter(SCRIPT), evaluator=FakeEvaluator(fail=True)
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.attempt.status is AttemptStatus.FAILED
    assert "evaluation" in (outcome.error or "")
    assert outcome.result is None
    assert len(sink.completed) == 1
    assert results.saved == []


def test_attempt_is_timestamped_and_the_input_is_not_mutated(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    runtime, _, _, _, _ = build_runtime(scenario, adapter=FakeInteractionAdapter(SCRIPT))

    outcome = asyncio.run(runtime.run(attempt))

    assert attempt.status is AttemptStatus.CREATED
    assert attempt.started_at is None
    assert outcome.attempt.started_at is not None
    assert outcome.attempt.ended_at is not None
    assert outcome.attempt.ended_at > outcome.attempt.started_at


def test_the_result_can_be_checked_against_its_framework(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    """The runtime stays framework-agnostic; the consumer checks shape after."""
    from osce_assessment.contracts import Competency, CompetencyDomain, CompetencyFramework

    framework = CompetencyFramework(
        id=FRAMEWORK.id,
        label="Checked afterwards",
        domains=(CompetencyDomain(id="skills", label="Skills"),),
        competencies=(
            Competency(id="structures_consultation", label="Structures", domain_id="skills"),
            Competency(id="uses_clear_language", label="Clear language", domain_id="skills"),
        ),
    )
    scores = {"structures_consultation": "A", "uses_clear_language": "G"}
    runtime, _, _, _, _ = build_runtime(
        scenario,
        adapter=FakeInteractionAdapter(SCRIPT),
        evaluator=FakeEvaluator(scores),
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.result is not None
    assert outcome.result.framework_id == FRAMEWORK.id
    framework.validate_scores(outcome.result.result)


@pytest.mark.parametrize("runs", [2, 3])
def test_running_the_same_attempt_again_does_not_redeliver(
    scenario: Scenario, attempt: AssessmentAttempt, runs: int
) -> None:
    sink = InMemoryTranscriptSink()
    runtime, _, _, _, _ = build_runtime(
        scenario, adapter=FakeInteractionAdapter(SCRIPT), sink=sink
    )

    async def run_many() -> list[bool]:
        return [(await runtime.run(attempt)).delivered for _ in range(runs)]

    delivered = asyncio.run(run_many())

    assert delivered[0] is True
    assert all(flag is False for flag in delivered[1:])
    assert sink.complete_calls == 1


def test_without_an_evaluator_the_runtime_stops_after_delivery(
    scenario: Scenario, attempt: AssessmentAttempt
) -> None:
    """A worker deployment: capture, deliver, hand off; the backend scores."""
    sink = InMemoryTranscriptSink()
    runtime = AttemptRuntime(
        scenario_provider=StaticScenarioProvider(scenario),
        profile_builder=SimpleProfileBuilder(),
        adapter=FakeInteractionAdapter(SCRIPT),
        transcript_sink=sink,
        retry_policy=RetryPolicy.immediate(),
        clock=_Clock(),
        id_factory=lambda: "msg-id",
    )

    outcome = asyncio.run(runtime.run(attempt))

    assert outcome.ok
    assert outcome.attempt.status is AttemptStatus.INTERACTION_COMPLETE
    assert outcome.result is None
    assert outcome.delivered is True
    assert len(sink.completed) == 1


def test_an_evaluator_without_a_policy_fails_the_attempt_after_delivery(attempt, scenario) -> None:
    from osce_assessment.runtime import AttemptRuntime, FakeInteractionAdapter

    bare = attempt.model_copy(update={"definition": attempt.definition.model_copy(update={"evaluation_policy": None})})
    sink = InMemoryTranscriptSink()
    runtime = AttemptRuntime(
        scenario_provider=StaticScenarioProvider(scenario), profile_builder=SimpleProfileBuilder(),
        adapter=FakeInteractionAdapter([(MessageRole.ASSISTANT, "Hi.")]), transcript_sink=sink,
        evaluator=FakeEvaluator(), result_sink=InMemoryResultSink(),
    )
    outcome = asyncio.run(runtime.run(bare))
    assert outcome.delivered and outcome.attempt.status is AttemptStatus.FAILED and "no evaluation policy" in outcome.error
