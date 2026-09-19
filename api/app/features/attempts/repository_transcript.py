"""Storage for an attempt's turns, its transcript record and its results.

Split from `repository.py` at the file cap; the attempt row and the things it
accumulates during and after a session change for different reasons.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import AssessmentResult, Transcript, TranscriptMessage


async def add_chunk(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    message_id: str,
    seq: int,
    role: str,
    message: str,
    spoken_at: datetime,
) -> TranscriptMessage:
    row = TranscriptMessage(
        attempt_id=attempt_id,
        message_id=message_id,
        seq=seq,
        role=role,
        message=message,
        spoken_at=spoken_at,
    )
    session.add(row)
    await session.flush()
    return row


async def chunks_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[TranscriptMessage]:
    stmt = (
        select(TranscriptMessage)
        .where(TranscriptMessage.attempt_id == attempt_id)
        .order_by(TranscriptMessage.seq)
    )
    return list((await session.execute(stmt)).scalars())


async def seen_message_ids(session: AsyncSession, attempt_id: uuid.UUID) -> set[str]:
    stmt = select(TranscriptMessage.message_id).where(TranscriptMessage.attempt_id == attempt_id)
    return set((await session.execute(stmt)).scalars())


async def transcript_for(session: AsyncSession, attempt_id: uuid.UUID) -> Transcript | None:
    stmt = select(Transcript).where(Transcript.attempt_id == attempt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_transcript_complete(
    session: AsyncSession, attempt_id: uuid.UUID, *, runtime_label: str | None, at: datetime
) -> Transcript:
    existing = await transcript_for(session, attempt_id)
    if existing is None:
        row = Transcript(attempt_id=attempt_id, complete=True, runtime_label=runtime_label, delivered_at=at)
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return row
    await session.execute(
        update(Transcript)
        .where(Transcript.attempt_id == attempt_id)
        .values(complete=True, runtime_label=runtime_label, delivered_at=at)
    )
    return existing


# --- results ---


async def save_result(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    framework_id: str,
    policy_version: str,
    payload: dict[str, Any],
    model_used: str | None,
    at: datetime,
) -> AssessmentResult:
    row = AssessmentResult(
        attempt_id=attempt_id,
        framework_id=framework_id,
        policy_version=policy_version,
        payload=payload,
        model_used=model_used,
        scored_at=at,
    )
    session.add(row)
    await session.flush()
    return row


async def results_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[AssessmentResult]:
    stmt = (
        select(AssessmentResult)
        .where(AssessmentResult.attempt_id == attempt_id)
        .order_by(AssessmentResult.scored_at)
    )
    return list((await session.execute(stmt)).scalars())


async def scored_policy_versions(session: AsyncSession, attempt_id: uuid.UUID) -> set[str]:
    stmt = select(AssessmentResult.policy_version).where(AssessmentResult.attempt_id == attempt_id)
    return set((await session.execute(stmt)).scalars())


async def attempt_ids_with_results(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these attempts have been marked, in one query.

    `recent_for_user` asks this per row, which is the N+1 every listing of
    attempts would otherwise repeat: a page of twenty attempts is twenty-one
    queries, and each of them loads whole payload documents to count them.
    """
    if not attempt_ids:
        return set()
    stmt = select(AssessmentResult.attempt_id).where(AssessmentResult.attempt_id.in_(list(attempt_ids)))
    return set((await session.execute(stmt)).scalars())
