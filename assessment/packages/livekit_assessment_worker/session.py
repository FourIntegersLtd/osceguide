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

from .adapter import LiveKitInteractionAdapter
from .bootstrap import Bootstrap, BootstrapError, fetch_bootstrap
from .metadata import MetadataError, parse_dispatch_metadata
from voice_infra.participants import other_agents_present, wait_for_candidate
from .sinks import HttpTranscriptSink

logger = logging.getLogger(__name__)

CANDIDATE_TIMEOUT_S = 120.0
SETTLE_S = 2.0
CANDIDATE_TIMEOUT_ENV = "LIVEKIT_ASSESSMENT_CANDIDATE_TIMEOUT_S"


def candidate_timeout_from_env() -> float:
    import os

    raw = (os.environ.get(CANDIDATE_TIMEOUT_ENV) or "").strip()
    try:
        return float(raw) if raw else CANDIDATE_TIMEOUT_S
    except ValueError:
        return CANDIDATE_TIMEOUT_S


class _BootstrappedScenario:
    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario

    def resolve(self, scenario_ref: ScenarioRef, attempt_context: Any) -> Scenario:
        return self._scenario


class _RenderedProfile:
    """The backend rendered the instructions already; pass them through."""

    def build(self, definition: AssessmentDefinition, scenario: Scenario) -> AIInteractionProfile:
        return definition.interaction_profile


class AssessmentSession:
    def __init__(self, registry: BackendRegistry, *, candidate_timeout: float | None = None, settle: float = SETTLE_S) -> None:
        self._registry = registry
        self._candidate_timeout = candidate_timeout_from_env() if candidate_timeout is None else candidate_timeout
        self._settle = settle

    async def entrypoint(self, ctx: Any) -> RuntimeOutcome | None:
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
        others = await other_agents_present(ctx.room, my_identity)
        if others:
            logger.warning("[assessment] other agents present %r; exiting to avoid a duplicate", others)
            return None

        try:
            bootstrap: Bootstrap = await asyncio.to_thread(fetch_bootstrap, endpoints, metadata)
        except BootstrapError as exc:
            logger.error("[assessment] bootstrap failed attempt=%s: %s", metadata.attempt_id, exc)
            return None

        try:
            candidate = await wait_for_candidate(ctx.room, metadata.candidate_ref, timeout=self._candidate_timeout)
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
                gender=bootstrap.scenario.patient_gender or "Female",
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
