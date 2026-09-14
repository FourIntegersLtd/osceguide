"""Drives one attempt from definition to stored result.

    resolve scenario → build profile → connect → greet → run interaction
    → stream every turn → deliver transcript once (retried)
    → evaluate → save result

The runtime never inspects ``attempt_context``; it only hands it to the ports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..contracts import (
    AssessmentAttempt,
    AssessmentResult,
    AttemptStatus,
    Evaluator,
    InteractionAdapter,
    ProfileBuilder,
    ResultSink,
    ScenarioProvider,
    Transcript,
    TranscriptSink,
)
from ._awaitable import maybe_await
from .collector import Clock, IdFactory, TranscriptCollector, new_message_id, utc_now
from .delivery import DeliveryError, RetryPolicy, TranscriptDelivery

logger = logging.getLogger(__name__)


@dataclass
class RuntimeOutcome:
    attempt: AssessmentAttempt
    transcript: Transcript
    result: AssessmentResult | None = None
    delivered: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class AttemptRuntime:
    def __init__(
        self,
        *,
        scenario_provider: ScenarioProvider,
        profile_builder: ProfileBuilder,
        adapter: InteractionAdapter,
        transcript_sink: TranscriptSink,
        evaluator: Evaluator,
        result_sink: ResultSink,
        retry_policy: RetryPolicy = RetryPolicy(),
        clock: Clock = utc_now,
        id_factory: IdFactory = new_message_id,
        runtime_label: str | None = None,
    ) -> None:
        self._scenarios = scenario_provider
        self._profiles = profile_builder
        self._adapter = adapter
        self._sink = transcript_sink
        self._evaluator = evaluator
        self._results = result_sink
        self._delivery = TranscriptDelivery(transcript_sink, policy=retry_policy)
        self._clock = clock
        self._id_factory = id_factory
        self._runtime_label = runtime_label

    async def deliver(self, transcript: Transcript) -> bool:
        """Idempotent transcript delivery; safe to call from several teardown paths."""
        return await self._delivery.deliver(transcript)

    async def run(self, attempt: AssessmentAttempt) -> RuntimeOutcome:
        attempt = attempt.model_copy(
            update={"status": AttemptStatus.RUNNING, "started_at": self._clock()}
        )
        definition = attempt.definition
        scenario = self._scenarios.resolve(definition.scenario_ref, attempt.attempt_context)
        profile = self._profiles.build(definition, scenario)
        collector = TranscriptCollector(
            attempt.attempt_id,
            self._sink,
            clock=self._clock,
            id_factory=self._id_factory,
            runtime_label=self._runtime_label,
        )

        interaction_error: Exception | None = None
        await self._adapter.connect()
        try:
            if profile.greeting:
                await self._adapter.send_greeting(profile.greeting)
            await self._adapter.run(profile, collector.on_message)
        except Exception as exc:  # noqa: BLE001 — partial transcript still delivered
            interaction_error = exc
            logger.warning("interaction failed attempt=%s: %r", attempt.attempt_id, exc)
        finally:
            try:
                await self._adapter.disconnect()
            except Exception as exc:  # noqa: BLE001 — never mask the outcome
                logger.warning("disconnect failed attempt=%s: %r", attempt.attempt_id, exc)

        transcript = collector.snapshot(complete=interaction_error is None)
        outcome = RuntimeOutcome(attempt=attempt, transcript=transcript)

        try:
            outcome.delivered = await self.deliver(transcript)
        except DeliveryError as exc:
            return self._finish(outcome, AttemptStatus.FAILED, error=str(exc))

        if interaction_error is not None:
            return self._finish(outcome, AttemptStatus.FAILED, error=repr(interaction_error))
        if not transcript.messages:
            return self._finish(outcome, AttemptStatus.INTERACTION_COMPLETE, error="empty_transcript")

        try:
            result = await maybe_await(
                self._evaluator.evaluate(attempt, transcript, definition.evaluation_policy)
            )
            await maybe_await(self._results.save_result(result, attempt.attempt_context))
        except Exception as exc:  # noqa: BLE001 — surfaced on the outcome
            return self._finish(outcome, AttemptStatus.FAILED, error=f"evaluation: {exc!r}")

        outcome.result = result
        return self._finish(outcome, AttemptStatus.EVALUATED)

    def _finish(
        self, outcome: RuntimeOutcome, status: AttemptStatus, *, error: str | None = None
    ) -> RuntimeOutcome:
        outcome.attempt = outcome.attempt.model_copy(
            update={"status": status, "ended_at": self._clock()}
        )
        outcome.error = error
        return outcome
