"""Incremental evidence on practice attempts, using the frozen rubric."""

import asyncio
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.settings import get_settings
from app.features.attempts import domain_definition, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.evaluator import FrozenFrameworkProvider
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import CoverageItemRead, CoverageRead
from app.features.attempts.service_reads import _ensure_visible, _require

PRACTICE_KINDS = frozenset({"practice", "set_station", "self_practice"})

# Published to the candidate's `/me/events` topic once a new coverage snapshot
# is written, so `LiveCoveragePanel` learns without polling every few seconds
# while a station is still running.
COVERAGE = "coverage"


def framework_for(attempt: Attempt) -> dict[str, Any] | None:
    """The competency framework this attempt's live panel should track, if it can support one."""
    if attempt.kind not in PRACTICE_KINDS:
        return None
    rubric = domain_definition.rubric_for(attempt.definition)
    framework = (rubric or {}).get("framework")
    return framework if isinstance(framework, dict) else None


async def read_coverage(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    requester_id: uuid.UUID,
) -> CoverageRead:
    """The competencies this candidate's consultation has touched so far, for the live panel.

    Only for a practice attempt with a rubric that supports it; anything else answers `supported=False`
    rather than an error, so the panel can hide itself quietly.
    """
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=False)
    framework = framework_for(attempt)
    if not framework:
        return CoverageRead(supported=False)
    provider = FrozenFrameworkProvider(framework)
    definition = provider.get(str(framework["id"]))
    labels = {competency.id: competency.label for competency in definition.competencies}
    snapshot = await repository.read(session, attempt_id) or {}
    return CoverageRead(
        supported=bool(definition.live_domain_ids),
        last_seq=snapshot.get("last_seq", -1),
        items=[
            CoverageItemRead(
                **coverage_item,
                label=labels.get(coverage_item["competency_id"], coverage_item["competency_id"]),
            )
            for coverage_item in snapshot.get("items", [])
        ],
    )


async def update_coverage(session: AsyncSession, attempt_id: uuid.UUID) -> None:
    """Called by serialised jobs; retries cannot erase previously earned evidence."""
    from osce_assessment.contracts import EvaluationPolicy, MessageRole, TranscriptMessage
    from osce_assessment.evaluation.live_coverage import CoverageSnapshot, LiveCoverageDetector

    from app.features.attempts.llm_clients import fallback_client, primary_client

    attempt = await repository.attempt_by_id(session, attempt_id)
    if attempt is None:
        return
    framework = framework_for(attempt)
    if not framework:
        return
    provider = FrozenFrameworkProvider(framework)
    framework_id = str(framework["id"])
    if not provider.get(framework_id).live_domain_ids:
        return
    previous = await repository.read(session, attempt_id)
    snapshot = (
        CoverageSnapshot.model_validate(previous) if previous else CoverageSnapshot(framework_id=framework_id)
    )
    turns = await transcripts.chunks_for(session, attempt_id)
    if not turns or max(turn.seq for turn in turns) <= snapshot.last_seq:
        return
    messages = tuple(
        TranscriptMessage(
            role=MessageRole.USER if turn.role in {"user", "doctor", "candidate"} else MessageRole.ASSISTANT,
            message=turn.message,
            timestamp=turn.spoken_at,
            message_id=turn.message_id,
            seq=turn.seq,
        )
        for turn in turns
    )
    settings = get_settings()
    policy = EvaluationPolicy(
        framework_id=framework_id,
        first_provider=settings.marking_primary_provider,
        openai_model=settings.marking_primary_model,
        openai_reasoning_effort=settings.marking_primary_effort,
        anthropic_model=settings.marking_fallback_model,
        version="live-coverage@1",
    )
    detector = LiveCoverageDetector(
        framework_provider=provider,
        primary_client=primary_client,
        fallback_client=fallback_client,
    )
    updated = await asyncio.to_thread(detector.detect, snapshot=snapshot, messages=messages, policy=policy)
    await repository.save(session, attempt_id, updated.model_dump(mode="json"))
    publish_after_commit(session, user_topic(attempt.user_id), COVERAGE, {"attempt_id": str(attempt_id)})
