"""Storage for the practice queue.

The session and history half is `repository_sessions.py`: joining, waiting and
matching are a different shape of query from reading, ending and remembering a
session that already exists.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, Visibility, addressed_to, audience_of
from app.features.peer_practice.models import QueueEntry


async def live_entry(session: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID) -> QueueEntry | None:
    stmt = select(QueueEntry).where(
        QueueEntry.user_id == user_id,
        QueueEntry.exam_id == exam_id,
        QueueEntry.status == "waiting",
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def entry_by_id(session: AsyncSession, entry_id: uuid.UUID) -> QueueEntry | None:
    stmt = select(QueueEntry).where(QueueEntry.id == entry_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def expire_stale_waiting(session: AsyncSession, *, at: datetime) -> int:
    """Mark waiting entries past their expiry as left."""
    expired = await session.execute(
        update(QueueEntry)
        .where(
            QueueEntry.status == "waiting",
            QueueEntry.expires_at.is_not(None),
            QueueEntry.expires_at < at,
        )
        .values(status="expired", left_at=at)
        .returning(QueueEntry.id)
    )
    return len(expired.scalars().all())


async def join(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    audience: Audience,
    expires_at: datetime | None = None,
) -> QueueEntry | None:
    """Take a place in the queue, or None if this person already holds one.

    `ON CONFLICT DO NOTHING` against the partial unique index, rather than a
    read and then an insert: two taps of the same button arriving together both
    found an empty queue and the loser answered 500. Nothing is rolled back on
    the conflict, so this stays inside the request's one transaction.
    """
    stmt = (
        pg_insert(QueueEntry)
        .values(
            user_id=user_id,
            exam_id=exam_id,
            visibility=str(audience.visibility),
            audience_org_id=audience.org_id,
            audience_group_id=audience.group_id,
            expires_at=expires_at,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "exam_id"], index_where=text("status = 'waiting'"))
        .returning(QueueEntry)
    )
    return (await session.execute(stmt)).scalars().one_or_none()


async def leave(session: AsyncSession, entry_id: uuid.UUID, *, at: datetime) -> bool:
    """Leave the queue. False when there was nothing to leave.

    The row count is returned rather than swallowed: the matcher may already
    have paired this person, and answering 204 to somebody who is still in a
    session tells them something untrue.
    """
    left = await session.execute(
        update(QueueEntry)
        .where(QueueEntry.id == entry_id, QueueEntry.status == "waiting")
        .values(status="left", left_at=at)
        .returning(QueueEntry.id)
    )
    return left.scalar_one_or_none() is not None


async def claim_waiting(
    session: AsyncSession, exam_id: uuid.UUID, *, audience: Audience, limit: int = 20
) -> list[QueueEntry]:
    """The people waiting in one room, oldest first, locked for matching."""
    stmt = (
        select(QueueEntry)
        .where(
            QueueEntry.exam_id == exam_id,
            QueueEntry.status == "waiting",
            addressed_to(QueueEntry, audience),
        )
        .order_by(QueueEntry.seq)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list((await session.execute(stmt)).scalars())


async def waiting_count(session: AsyncSession, exam_id: uuid.UUID, *, audience: Audience) -> int:
    """How many are waiting in this room."""
    stmt = select(func.count(QueueEntry.id)).where(
        QueueEntry.exam_id == exam_id,
        QueueEntry.status == "waiting",
        addressed_to(QueueEntry, audience),
    )
    return int((await session.execute(stmt)).scalar_one())


async def waiting_audiences(session: AsyncSession, exam_id: uuid.UUID) -> list[Audience]:
    """Every room with somebody waiting in it, for this exam."""
    stmt = (
        select(QueueEntry.visibility, QueueEntry.audience_org_id, QueueEntry.audience_group_id)
        .where(QueueEntry.exam_id == exam_id, QueueEntry.status == "waiting")
        .distinct()
    )
    return [
        Audience(visibility=Visibility(audience_row[0]), org_id=audience_row[1], group_id=audience_row[2])
        for audience_row in (await session.execute(stmt)).all()
    ]


async def position_of(session: AsyncSession, entry: QueueEntry) -> int:
    """How many people are ahead. One-based."""
    stmt = select(func.count(QueueEntry.id)).where(
        QueueEntry.exam_id == entry.exam_id,
        QueueEntry.status == "waiting",
        QueueEntry.seq < entry.seq,
        addressed_to(QueueEntry, audience_of(entry)),
    )
    return int((await session.execute(stmt)).scalar_one()) + 1


async def mark_matched(session: AsyncSession, entry_ids: list[uuid.UUID], *, session_id: uuid.UUID) -> None:
    await session.execute(
        update(QueueEntry)
        .where(QueueEntry.id.in_(entry_ids))
        .values(status="matched", matched_session_id=session_id)
    )
