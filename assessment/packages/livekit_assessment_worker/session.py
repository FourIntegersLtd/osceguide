"""One job: metadata → bootstrap → candidate → runtime → delivered transcript."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from livekit.agents import AutoSubscribe
from osce_assessment.contracts import AIInteractionProfile, AssessmentDefinition, Scenario, ScenarioRef
from osce_assessment.runtime import AttemptRuntime, RuntimeOutcome
from voice_infra import BackendRegistry
from voice_infra.cloud_slot import register_cloud_slot_lifecycle
from voice_infra.participants import Outranked, agents_with_priority, wait_for_candidate
from voice_infra.worker_config import optional_float

from .adapter import LiveKitInteractionAdapter
from .bootstrap import Bootstrap, BootstrapError, fetch_bootstrap
from .metadata import MetadataError, parse_dispatch_metadata
from .sinks import HttpTranscriptSink

logger = logging.getLogger(__name__)

CANDIDATE_TIMEOUT_S = 120.0
SETTLE_S = 2.0
CANDIDATE_TIMEOUT_ENV = "LIVEKIT_ASSESSMENT_CANDIDATE_TIMEOUT_S"


def candidate_timeout_from_env() -> float:
    return optional_float(CANDIDATE_TIMEOUT_ENV, CANDIDATE_TIMEOUT_S)


class _BootstrappedScenario:
    """A scenario provider that returns the scenario the backend already sent in the bootstrap."""

    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario

    def resolve(self, scenario_ref: ScenarioRef, attempt_context: Any) -> Scenario:
        return self._scenario


class _RenderedProfile:
    """The backend rendered the instructions already; pass them through."""

    def build(self, definition: AssessmentDefinition, scenario: Scenario) -> AIInteractionProfile:
        return definition.interaction_profile


class AssessmentSession:
    """One job's run of an assessment room, from joining to handing back the transcript."""

    def __init__(self, registry: BackendRegistry, *, candidate_timeout: float | None = None, settle: float = SETTLE_S) -> None:
        self._registry = registry
        self._candidate_timeout = candidate_timeout_from_env() if candidate_timeout is None else candidate_timeout
        self._settle = settle

    async def entrypoint(self, ctx: Any) -> RuntimeOutcome | None:
        """Run the job: read the dispatch metadata, join the room, and run the interaction unless another worker holds it."""
        try:
            metadata = parse_dispatch_metadata(getattr(ctx.job, "metadata", None))
        except MetadataError as exc:
            logger.error("[assessment] rejected job: %s", exc)
            return None
        endpoints = self._registry.get(metadata.backend)

        await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        ctx.log_context_fields = {"room": ctx.room.name, "attempt": metadata.attempt_id}
        register_cloud_slot_lifecycle(ctx, endpoints)

        await asyncio.sleep(self._settle)
        my_identity = ctx.room.local_participant.identity
        holders = await agents_with_priority(ctx.room, my_identity)
        if holders:
            # Only to an identity that sorts before mine, so a duplicate
            # dispatch leaves exactly one agent rather than two or none.
            _leave(ctx, holders[0])
            return None

        try:
            bootstrap: Bootstrap = await asyncio.to_thread(fetch_bootstrap, endpoints, metadata)
        except BootstrapError as exc:
            logger.error("[assessment] bootstrap failed attempt=%s: %s", metadata.attempt_id, exc)
            return None

        try:
            candidate = await wait_for_candidate(
                ctx.room,
                metadata.candidate_ref,
                timeout=self._candidate_timeout,
                my_identity=my_identity,
            )
        except Outranked as holder:
            # A duplicate dispatch that had not joined yet when the check above
            # ran. Whoever sorts first keeps the room, so exactly one stays.
            _leave(ctx, str(holder))
            return None
        except asyncio.TimeoutError:
            logger.warning("[assessment] no candidate joined within %ss attempt=%s", self._candidate_timeout, metadata.attempt_id)
            return None
        logger.info("[assessment] candidate joined identity=%s attempt=%s", candidate.identity, metadata.attempt_id)

        runtime = AttemptRuntime(
            scenario_provider=_BootstrappedScenario(bootstrap.scenario),
            profile_builder=_RenderedProfile(),
            adapter=LiveKitInteractionAdapter(
                ctx,
                candidate_identity=candidate.identity,
                gender=bootstrap.scenario.patient_gender,
                label=f"assessment:{bootstrap.attempt.definition.interaction_profile.mode.value}",
            ),
            transcript_sink=HttpTranscriptSink(endpoints),
            runtime_label="livekit",
        )
        outcome = await runtime.run(bootstrap.attempt)
        logger.info(
            "[assessment] finished attempt=%s status=%s delivered=%s error=%s",
            metadata.attempt_id, outcome.attempt.status.value, outcome.delivered, outcome.error,
        )
        return outcome


def _leave(ctx: Any, holder: str) -> None:
    """Give up the room to ``holder``, and actually go.

    Returning from the entrypoint ends this job's work but leaves the agent
    connected, so a yielding duplicate stayed in the room as a silent second
    participant — which is what a candidate, and the duplicate-dispatch test,
    both see. Shutting the job down is what removes it.

    Defensive about `shutdown` for the same reason the assistant worker is:
    the outcome here is that this agent stops, and a context that cannot be
    shut down must not turn that into an exception on the way out.
    """
    logger.warning("[assessment] yielding the room to %s", holder)
    try:
        ctx.shutdown(reason=f"duplicate_of_{holder}")
    except Exception as exc:  # noqa: BLE001 — leaving is best-effort
        logger.warning("[assessment] shutdown after yielding failed: %s", exc)
