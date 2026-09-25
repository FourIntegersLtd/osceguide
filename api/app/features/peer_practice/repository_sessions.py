"""Storage for one matched practice session, and the history it leaves behind.

`repository.py` keeps the queue half: joining, waiting and matching are a
different shape of query from reading, ending and remembering a session that
already exists.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.peer_practice.models import PracticeHistory, PracticeSession


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


async def record_feedback(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    rating: int,
    comment: str | None,
    would_practice_again: bool | None = None,
) -> None:
    await session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == session_id)
        .values(feedback_rating=rating, feedback_comment=comment, would_practice_again=would_practice_again)
    )


async def advance_phase(
    session: AsyncSession, session_id: uuid.UUID, *, values: Mapping[str, object]
) -> None:
    await session.execute(update(PracticeSession).where(PracticeSession.id == session_id).values(**values))


async def set_recording_started(
    session: AsyncSession, session_id: uuid.UUID, *, egress_id: str, key: str
) -> None:
    """Record that a recording is running, and where it will land.

    Guarded on the state rather than written blind: two presence heartbeats can
    observe the same phase change, and the second must not overwrite the first
    recording's id with its own and orphan a running egress.
    """
    await session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == session_id, PracticeSession.recording_state == "none")
        .values(egress_id=egress_id, recording_key=key, recording_state="recording")
    )


async def set_recording_state(
    session: AsyncSession, session_id: uuid.UUID, *, state: str, error: str | None = None
) -> None:
    await session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == session_id)
        .values(recording_state=state, recording_error=error)
    )


async def set_doctor_attempt(session: AsyncSession, session_id: uuid.UUID, *, attempt_id: uuid.UUID) -> None:
    await session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == session_id)
        .values(doctor_attempt_id=attempt_id, recording_state="scored", recording_error=None)
    )
