"""Joining the queue, being matched, and practising."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repo
from app.features.catalog.service import resolve_exam
from app.features.peer_practice import domain, errors, repository
from app.features.peer_practice.models import PracticeSession, QueueEntry
from app.features.peer_practice.schemas import PracticeSessionRead, QueueStatus


async def join_queue(session: AsyncSession, *, user_id: uuid.UUID, exam_code: str) -> QueueStatus:
    """Take a place in the queue, or keep the one you have.

    Joining twice is not an error worth refusing outright — it is somebody
    tapping a button again — so it returns the place they already hold.
    """
    exam = await resolve_exam(session, exam_code)
    existing = await repository.live_entry(session, user_id, exam.id)
    entry = existing or await repository.join(session, user_id=user_id, exam_id=exam.id)
    return await _status(session, entry)


async def read_status(session: AsyncSession, entry_id: uuid.UUID, *, user_id: uuid.UUID) -> QueueStatus:
    entry = await repository.entry_by_id(session, entry_id)
    if entry is None or entry.user_id != user_id:
        raise errors.QueueEntryNotFound()
    return await _status(session, entry)


async def leave_queue(
    session: AsyncSession, entry_id: uuid.UUID, *, user_id: uuid.UUID, now: datetime
) -> None:
    entry = await repository.entry_by_id(session, entry_id)
    if entry is None or entry.user_id != user_id:
        raise errors.QueueEntryNotFound()
    await repository.leave(session, entry_id, at=now)


async def match_waiting(session: AsyncSession, exam_id: uuid.UUID) -> PracticeSession | None:
    """Pair the next two people who can practise together.

    The queue rows are locked while this runs, so two matchers pair different
    people rather than both pairing the same two.
    """
    entries = await repository.claim_waiting(session, exam_id)
    if len(entries) < 2:
        return None

    waiting: list[domain.Waiting] = []
    by_user: dict[str, QueueEntry] = {}
    for entry in entries:
        history = await repository.history_for(session, entry.user_id)
        waiting.append(
            domain.Waiting(
                user_id=str(entry.user_id),
                last_role=domain.Role(history.last_role) if history and history.last_role else None,
                session_count=history.session_count if history else 0,
                never_doctor=history.never_doctor if history else False,
            )
        )
        by_user[str(entry.user_id)] = entry

    pair = domain.next_pair(waiting)
    if pair is None:
        return None

    doctor_id, patient_id = uuid.UUID(pair.doctor), uuid.UUID(pair.patient)
    practice = await repository.create_session(
        session, exam_id=exam_id, doctor_user_id=doctor_id, patient_user_id=patient_id
    )
    await repository.set_room(session, practice.id, room_name=f"practice_{practice.id}")
    await repository.mark_matched(
        session,
        [by_user[pair.doctor].id, by_user[pair.patient].id],
        session_id=practice.id,
    )
    # Recorded now rather than at the end, so somebody who abandons a session
    # still does not get the same part twice running.
    await repository.record_role(session, doctor_id, role=str(domain.Role.DOCTOR))
    await repository.record_role(session, patient_id, role=str(domain.Role.PATIENT))
    return await repository.session_by_id(session, practice.id)


async def read_session(
    session: AsyncSession, session_id: uuid.UUID, *, user_id: uuid.UUID
) -> PracticeSessionRead:
    row = await repository.session_by_id(session, session_id)
    if row is None or user_id not in {row.doctor_user_id, row.patient_user_id}:
        # 404 rather than 403: a session id is not something a stranger should
        # be able to confirm exists.
        raise errors.SessionNotFound()
    return await _session_read(session, row, viewer_id=user_id)


async def end_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    reason: str | None,
    now: datetime,
) -> PracticeSessionRead:
    row = await repository.session_by_id(session, session_id)
    if row is None or user_id not in {row.doctor_user_id, row.patient_user_id}:
        raise errors.SessionNotFound()
    if row.status == "ended":
        raise errors.SessionAlreadyEnded()
    await repository.end_session(session, session_id, at=now, reason=reason)
    refreshed = await repository.session_by_id(session, session_id)
    return await _session_read(session, refreshed, viewer_id=user_id)  # type: ignore[arg-type]


async def list_my_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[PracticeSessionRead]:
    return [
        await _session_read(session, row, viewer_id=user_id)
        for row in await repository.sessions_for_user(session, user_id)
    ]


async def _status(session: AsyncSession, entry: QueueEntry) -> QueueStatus:
    return QueueStatus(
        entry_id=entry.id,
        status=entry.status,
        position=await repository.position_of(session, entry) if entry.status == "waiting" else None,
        waiting_count=await repository.waiting_count(session, entry.exam_id),
        session_id=entry.matched_session_id,
    )


async def _session_read(
    session: AsyncSession, row: PracticeSession, *, viewer_id: uuid.UUID
) -> PracticeSessionRead:
    exam = await catalog_repo.exam_by_id(session, row.exam_id)
    is_doctor = row.doctor_user_id == viewer_id
    return PracticeSessionRead(
        id=row.id,
        exam_code=exam.code if exam else "",
        my_role=str(domain.Role.DOCTOR if is_doctor else domain.Role.PATIENT),
        partner_user_id=row.patient_user_id if is_doctor else row.doctor_user_id,
        room_name=row.room_name,
        status=row.status,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )
