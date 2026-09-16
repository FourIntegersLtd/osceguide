"""Storage for the practice queue, its sessions and its history."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, literal, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

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


async def join(session: AsyncSession, *, user_id: uuid.UUID, exam_id: uuid.UUID) -> QueueEntry:
    row = QueueEntry(user_id=user_id, exam_id=exam_id)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def leave(session: AsyncSession, entry_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(
        update(QueueEntry)
        .where(QueueEntry.id == entry_id, QueueEntry.status == "waiting")
        .values(status="left", left_at=at)
    )


async def claim_waiting(session: AsyncSession, exam_id: uuid.UUID, *, limit: int = 20) -> list[QueueEntry]:
    """The people waiting, oldest first, locked for matching.

    `FOR UPDATE SKIP LOCKED` so two matchers running at once pair different
    people rather than both pairing the same two.
    """
    stmt = (
        select(QueueEntry)
        .where(QueueEntry.exam_id == exam_id, QueueEntry.status == "waiting")
        .order_by(QueueEntry.created_at, QueueEntry.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list((await session.execute(stmt)).scalars())


async def waiting_count(session: AsyncSession, exam_id: uuid.UUID) -> int:
    stmt = select(func.count(QueueEntry.id)).where(
        QueueEntry.exam_id == exam_id, QueueEntry.status == "waiting"
    )
    return int((await session.execute(stmt)).scalar_one())


async def position_of(session: AsyncSession, entry: QueueEntry) -> int:
    """How many people are ahead. One-based, so "position 1" means next.

    Ties break on id, as the ordering everywhere else does: two people joining
    in the same transaction share a `now()`, and without the tie-break they
    would both be told they are next.
    """
    stmt = select(func.count(QueueEntry.id)).where(
        QueueEntry.exam_id == entry.exam_id,
        QueueEntry.status == "waiting",
        tuple_(QueueEntry.created_at, QueueEntry.id) < tuple_(literal(entry.created_at), literal(entry.id)),
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
) -> PracticeSession:
    row = PracticeSession(exam_id=exam_id, doctor_user_id=doctor_user_id, patient_user_id=patient_user_id)
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
