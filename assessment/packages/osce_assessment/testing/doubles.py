"""In-memory implementations of the ports."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from ..contracts import (
    AIInteractionProfile,
    AssessmentAttempt,
    AssessmentDefinition,
    AssessmentResult,
    EvaluationPolicy,
    Scenario,
    ScenarioRef,
    Transcript,
    TranscriptMessage,
)


class StaticScenarioProvider:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.calls: list[tuple[ScenarioRef, dict[str, str]]] = []

    def resolve(self, scenario_ref: ScenarioRef, attempt_context: Mapping[str, str]) -> Scenario:
        self.calls.append((scenario_ref, dict(attempt_context)))
        return self.scenario


class SimpleProfileBuilder:
    """Fills ``instructions`` from the scenario; keeps everything else as defined."""

    def build(self, definition: AssessmentDefinition, scenario: Scenario) -> AIInteractionProfile:
        template = definition.interaction_profile
        brief_lines = [f"{key}: {value}" for key, value in scenario.patient_brief.items()]
        instructions = "\n".join(
            [f"Scenario: {scenario.title}", f"Mode: {template.mode.value}", *brief_lines]
        )
        return template.model_copy(update={"instructions": instructions})


class InMemoryTranscriptSink:
    def __init__(self, *, fail_complete_times: int = 0, fail_append: bool = False) -> None:
        self.appended: list[tuple[str, TranscriptMessage]] = []
        self.completed: list[tuple[str, Transcript]] = []
        self.complete_calls = 0
        self._fail_complete_times = fail_complete_times
        self._fail_append = fail_append

    def append(self, attempt_id: str, message: TranscriptMessage) -> None:
        if self._fail_append:
            raise ConnectionError("append sink unavailable")
        self.appended.append((attempt_id, message))

    def complete(self, attempt_id: str, transcript: Transcript) -> None:
        self.complete_calls += 1
        if self._fail_complete_times > 0:
            self._fail_complete_times -= 1
            raise ConnectionError("complete sink unavailable")
        self.completed.append((attempt_id, transcript))


class FakeEvaluator:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        *,
        provider: str = "fake",
        model: str = "fake-model",
        fail: bool = False,
    ) -> None:
        self.payload = payload or {"overall": "competent"}
        self.provider = provider
        self.model = model
        self.fail = fail
        self.calls: list[tuple[AssessmentAttempt, Transcript, EvaluationPolicy]] = []

    def evaluate(
        self, attempt: AssessmentAttempt, transcript: Transcript, policy: EvaluationPolicy
    ) -> AssessmentResult:
        self.calls.append((attempt, transcript, policy))
        if self.fail:
            raise RuntimeError("evaluator unavailable")
        return AssessmentResult(
            attempt_id=attempt.attempt_id,
            framework_id=policy.framework_id,
            policy_version=policy.version,
            result=dict(self.payload),
            provider=self.provider,
            model=self.model,
            generated_at=datetime.now(timezone.utc),
            raw_metadata={"message_count": len(transcript.messages)},
        )


class InMemoryResultSink:
    def __init__(self) -> None:
        self.saved: list[tuple[AssessmentResult, dict[str, str]]] = []

    def save_result(self, result: AssessmentResult, attempt_context: Mapping[str, str]) -> None:
        self.saved.append((result, dict(attempt_context)))
