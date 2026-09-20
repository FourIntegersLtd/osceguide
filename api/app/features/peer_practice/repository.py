"""Storage for the practice queue, its sessions and its history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import Audience, Visibility, addressed_to, audience_of
from app.features.peer_practice.models import PracticeHistory, PracticeSession, QueueEntry


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
    """The people waiting in one room, oldest first, locked for matching.

    `FOR UPDATE SKIP LOCKED` so two matchers running at once pair different
    people rather than both pairing the same two. Scoped to one room, because
    pairing across rooms is what the audience exists to prevent.
    """
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
    """How many are waiting in this room.

    Per room, not per exam: somebody queueing inside their institution was
    otherwise told twelve people were ahead of them when only two could ever
    be matched with them.
    """
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
        Audience(visibility=Visibility(row[0]), org_id=row[1], group_id=row[2])
        for row in (await session.execute(stmt)).all()
    ]


async def position_of(session: AsyncSession, entry: QueueEntry) -> int:
    """How many people are ahead. One-based, so "position 1" means next.

    Counted on `seq`, not on `created_at`: everyone joining in one transaction
    shares a timestamp, and a random-uuid tie-break gives a stable order that is
    not the order they arrived in — two people would each be told they were next.
    """
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


async def create_session(
    session: AsyncSession,
    *,
    exam_id: uuid.UUID,
    doctor_user_id: uuid.UUID,
    patient_user_id: uuid.UUID,
    station_version_id: uuid.UUID | None = None,
    peer_session_id: uuid.UUID | None = None,
) -> PracticeSession:
    row = PracticeSession(
        exam_id=exam_id,
        doctor_user_id=doctor_user_id,
        patient_user_id=patient_user_id,
        station_version_id=station_version_id,
        peer_session_id=peer_session_id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def set_room(session: AsyncSession, session_id: uuid.UUID, *, room_name: str) -> None:
    await session.execute(
        update(PracticeSession).where(PracticeSession.id == session_id).values(room_name=room_name)
    )


async def session_by_id(session: AsyncSession, session_id: uuid.UUID) -> PracticeSession | None:
    stmt = select(PracticeSession).where(PracticeSession.id == session_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def end_session(
    session: AsyncSession, session_id: uuid.UUID, *, at: datetime, reason: str | None
) -> None:
    await session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == session_id)
        .values(status="ended", ended_at=at, end_reason=reason)
    )


async def sessions_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 50
) -> list[PracticeSession]:
    stmt = (
        select(PracticeSession)
        .where(
            or_(
                PracticeSession.doctor_user_id == user_id,
                PracticeSession.patient_user_id == user_id,
            )
        )
        .order_by(PracticeSession.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


# --- history ---------------------------------------------------------------


async def history_for(session: AsyncSession, user_id: uuid.UUID) -> PracticeHistory | None:
    stmt = select(PracticeHistory).where(PracticeHistory.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def record_role(session: AsyncSession, user_id: uuid.UUID, *, role: str) -> None:
    """Remember the part someone played, so they take the other one next time."""
    existing = await history_for(session, user_id)
    if existing is None:
        session.add(PracticeHistory(user_id=user_id, last_role=role, session_count=1))
        await session.flush()
        return
    await session.execute(
        update(PracticeHistory)
        .where(PracticeHistory.user_id == user_id)
        .values(last_role=role, session_count=PracticeHistory.session_count + 1)
    )
