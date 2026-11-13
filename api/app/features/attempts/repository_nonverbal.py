"""Storage for non-verbal consent, the per-second batches and the written summary."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, exists, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import (
    Attempt,
    AttemptNonverbalBatch,
    AttemptNonverbalSummary,
    NonverbalConsent,
)


async def consent_for(session: AsyncSession, user_id: uuid.UUID) -> NonverbalConsent | None:
    """This person's consent row, withdrawn or not."""
    return await session.get(NonverbalConsent, user_id)


async def upsert_consent(session: AsyncSession, user_id: uuid.UUID, *, version: str, at: datetime) -> None:
    """Record consent, clearing any earlier withdrawal."""
    stmt = insert(NonverbalConsent).values(user_id=user_id, version=version, consented_at=at)
    stmt = stmt.on_conflict_do_update(
        index_elements=[NonverbalConsent.user_id],
        set_={"version": version, "consented_at": at, "withdrawn_at": None},
    )
    await session.execute(stmt)


async def withdraw_consent(session: AsyncSession, user_id: uuid.UUID, *, at: datetime) -> None:
    """Mark consent withdrawn; a person who never consented has no row to change."""
    await session.execute(
        update(NonverbalConsent).where(NonverbalConsent.user_id == user_id).values(withdrawn_at=at)
    )


async def add_batch(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    seq: int,
    skew_ms: int,
    samples: list[dict[str, Any]],
    at: datetime,
) -> bool:
    """Store one batch; False when this sequence number was already stored (the browser may repeat)."""
    stmt = (
        insert(AttemptNonverbalBatch)
        .values(attempt_id=attempt_id, seq=seq, skew_ms=skew_ms, samples=samples, received_at=at)
        .on_conflict_do_nothing(index_elements=["attempt_id", "seq"])
        .returning(AttemptNonverbalBatch.seq)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def batches_for(session: AsyncSession, attempt_id: uuid.UUID) -> list[AttemptNonverbalBatch]:
    """Every stored batch of this attempt, in sequence order."""
    stmt = (
        select(AttemptNonverbalBatch)
        .where(AttemptNonverbalBatch.attempt_id == attempt_id)
        .order_by(AttemptNonverbalBatch.seq)
    )
    return list((await session.execute(stmt)).scalars())


async def has_batches(session: AsyncSession, attempt_id: uuid.UUID) -> bool:
    """Whether any batch is stored for this attempt."""
    stmt = select(AttemptNonverbalBatch.seq).where(AttemptNonverbalBatch.attempt_id == attempt_id).limit(1)
    return (await session.execute(stmt)).first() is not None


async def save_summary(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    state: str,
    facts: dict[str, Any],
    feedback: dict[str, Any] | None,
    model_used: str | None,
    at: datetime,
) -> None:
    """Store the summary once; a second write for the same attempt is ignored."""
    stmt = (
        insert(AttemptNonverbalSummary)
        .values(
            attempt_id=attempt_id,
            state=state,
            facts=facts,
            feedback=feedback,
            model_used=model_used,
            created_at=at,
        )
        .on_conflict_do_nothing(index_elements=["attempt_id"])
    )
    await session.execute(stmt)


async def summary_for(session: AsyncSession, attempt_id: uuid.UUID) -> AttemptNonverbalSummary | None:
    """The stored summary row, if one was written."""
    return await session.get(AttemptNonverbalSummary, attempt_id)


async def delete_batches(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> int:
    """Delete the raw per-second batches of these attempts. Answers how many rows went."""
    if not attempt_ids:
        return 0
    result = await session.execute(
        delete(AttemptNonverbalBatch).where(AttemptNonverbalBatch.attempt_id.in_(attempt_ids))
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def orphan_batch_attempt_ids(
    session: AsyncSession, *, cutoff: datetime, open_statuses: Sequence[str], limit: int
) -> list[uuid.UUID]:
    """Attempts holding batches older than `cutoff` that no summary job is still going to read.

    Either the attempt is not open (abandoned, failed, or finished without the job queueing), or a
    summary already exists and a late batch landed after the job ran.
    """
    summarised = exists().where(AttemptNonverbalSummary.attempt_id == Attempt.id)
    stmt = (
        select(AttemptNonverbalBatch.attempt_id)
        .join(Attempt, Attempt.id == AttemptNonverbalBatch.attempt_id)
        .where(
            AttemptNonverbalBatch.received_at < cutoff,
            or_(Attempt.status.not_in(open_statuses), summarised),
        )
        .distinct()
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def delete_all_for_attempts(session: AsyncSession, attempt_ids: Sequence[uuid.UUID]) -> None:
    """Delete batches and summaries of these attempts, for erasure, retention and withdrawn consent."""
    if attempt_ids:
        await delete_batches(session, attempt_ids)
        await session.execute(
            delete(AttemptNonverbalSummary).where(AttemptNonverbalSummary.attempt_id.in_(attempt_ids))
        )
