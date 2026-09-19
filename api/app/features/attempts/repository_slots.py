"""The attempt rows that belong to an exam slot.

Split from `repository.py` at the file cap, along the line the slice already
had: everything here is about an attempt somebody was *dispatched* into during
an examination — which one is live on a slot, failing it when the supervisor
redispatches, and which slots have one at all. The rest of that file is the
attempt a person starts for themselves.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.domain import Status
from app.features.attempts.models import Attempt
from app.features.attempts.repository import set_status


async def live_attempts_for_slots(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> list[Attempt]:
    """The one unfailed attempt on each of these slots, for a screen that lists them."""
    if not slot_ids:
        return []
    stmt = select(Attempt).where(Attempt.slot_id.in_(list(slot_ids)), Attempt.status != "failed")
    return list((await session.execute(stmt)).scalars())


async def live_attempt_for_slot(session: AsyncSession, slot_id: uuid.UUID) -> Attempt | None:
    stmt = select(Attempt).where(Attempt.slot_id == slot_id, Attempt.status != "failed")
    return (await session.execute(stmt)).scalar_one_or_none()


async def fail_live_attempt_for_slot(
    session: AsyncSession, slot_id: uuid.UUID, *, at: datetime, reason: str
) -> None:
    """Fail whatever is still live on this slot, and make it visible.

    Flushed here because the insert that follows has to see it: the partial
    unique index on `(slot_id) where status <> 'failed'` would otherwise refuse
    the new attempt.
    """
    live = await live_attempt_for_slot(session, slot_id)
    if live is None:
        return
    await set_status(session, live.id, status=Status.FAILED, at=at, reason=reason)
    await session.flush()


async def exam_for_slot_attempt(session: AsyncSession, slot_id: uuid.UUID) -> uuid.UUID | None:
    """The exam a previous attempt on this slot ran under.

    Reused on re-dispatch so a retry is marked against the same framework as
    the recording it replaces.
    """
    stmt = (
        select(Attempt.exam_id).where(Attempt.slot_id == slot_id).order_by(Attempt.created_at.desc()).limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def slots_with_attempts(session: AsyncSession, slot_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    if not slot_ids:
        return set()
    stmt = select(Attempt.slot_id).where(Attempt.slot_id.in_(list(slot_ids))).distinct()
    return {row for row in (await session.execute(stmt)).scalars() if row is not None}
