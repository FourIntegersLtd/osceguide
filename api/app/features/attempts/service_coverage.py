"""Incremental evidence on practice attempts, using the frozen rubric."""

import asyncio
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.attempts import domain_definition, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.evaluator import FrozenFrameworkProvider
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import CoverageItemRead, CoverageRead
from app.features.attempts.service_reads import _ensure_visible, _require

PRACTICE_KINDS = frozenset({"practice", "set_station", "self_practice"})


def framework_for(attempt: Attempt) -> dict[str, Any] | None:
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
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=False)
    framework = framework_for(attempt)
    if not framework:
        return CoverageRead(supported=False)
    provider = FrozenFrameworkProvider(framework)
    definition = provider.get(str(framework["id"]))
    labels = {item.id: item.label for item in definition.competencies}
    snapshot = await repository.read(session, attempt_id) or {}
    return CoverageRead(
        supported=bool(definition.live_domain_ids),
        last_seq=snapshot.get("last_seq", -1),
        items=[
            CoverageItemRead(**item, label=labels.get(item["competency_id"], item["competency_id"]))
            for item in snapshot.get("items", [])
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
        primary_model=settings.marking_primary_model,
        primary_reasoning_effort=settings.marking_primary_effort,
        fallback_model=settings.marking_fallback_model,
        version="live-coverage@1",
    )
    detector = LiveCoverageDetector(
        framework_provider=provider,
        primary_client=primary_client,
        fallback_client=fallback_client,
    )
    updated = await asyncio.to_thread(detector.detect, snapshot=snapshot, messages=messages, policy=policy)
    await repository.save(session, attempt_id, updated.model_dump(mode="json"))
