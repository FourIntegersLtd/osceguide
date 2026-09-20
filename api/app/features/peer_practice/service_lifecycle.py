"""Presence, phased timing, and marketplace runtime sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.features.catalog import service as catalog
from app.features.peer_practice import domain, repository
from app.features.peer_practice.models import PracticeSession
SESSION_UPDATED = "practice.session_updated"
from app.features.peer_practice.station_pick import pick_station_version_id
from app.features.peer_practice.timers import durations_for


async def roles_for_peer_participants(
    session: AsyncSession, owner_id: uuid.UUID, claimer_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """Doctor and patient user ids for a booked pair."""
    histories = []
    for user_id in (owner_id, claimer_id):
        history = await repository.history_for(session, user_id)
        histories.append(
            domain.Waiting(
                user_id=str(user_id),
                last_role=domain.Role(history.last_role) if history and history.last_role else None,
                session_count=history.session_count if history else 0,
                never_doctor=history.never_doctor if history else False,
            )
        )
    pair = domain.next_pair(histories)
    if pair is None:
        # Fallback: owner is doctor if pairing rules cannot decide.
        return owner_id, claimer_id
    return uuid.UUID(pair.doctor), uuid.UUID(pair.patient)


async def create_runtime_for_peer_booking(
    session: AsyncSession,
    *,
    peer_session_id: uuid.UUID,
    exam_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    claimer_user_id: uuid.UUID,
) -> PracticeSession:
    doctor_id, patient_id = await roles_for_peer_participants(session, owner_user_id, claimer_user_id)
    station_id = await pick_station_version_id(session, exam_id=exam_id, doctor_user_id=doctor_id)
    practice = await repository.create_session(
        session,
        exam_id=exam_id,
        doctor_user_id=doctor_id,
        patient_user_id=patient_id,
        station_version_id=station_id,
        peer_session_id=peer_session_id,
    )
    await repository.set_room(session, practice.id, room_name=f"practice_{practice.id}")
    await repository.record_role(session, doctor_id, role=str(domain.Role.DOCTOR))
    await repository.record_role(session, patient_id, role=str(domain.Role.PATIENT))
    return practice


async def advance_phases_if_due(
    session: AsyncSession, row: PracticeSession, *, exam_code: str, now: datetime
) -> PracticeSession:
    if row.status == "ended" or row.current_phase is None or row.phase_ends_at is None:
        return row
    if now < row.phase_ends_at:
        return row
    durs = durations_for(exam_code)
    next_phase: str | None = None
    next_end: datetime | None = None
    if row.current_phase == "preparation":
        next_phase = "consultation"
        next_end = now + timedelta(seconds=durs.consultation)
        started_at = now
    elif row.current_phase == "consultation":
        next_phase = "debrief"
        next_end = now + timedelta(seconds=durs.debrief)
        started_at = row.started_at
    elif row.current_phase == "debrief":
        next_phase = "completed"
        next_end = None
        started_at = row.started_at
    else:
        return row
    values: dict[str, object] = {"current_phase": next_phase, "phase_ends_at": next_end}
    if row.current_phase == "preparation":
        values["started_at"] = started_at
    if next_phase == "completed":
        values["status"] = "ended"
        values["ended_at"] = now
        values["end_reason"] = "phases_complete"
    await session.execute(update(PracticeSession).where(PracticeSession.id == row.id).values(**values))
    refreshed = await repository.session_by_id(session, row.id)
    assert refreshed is not None
    for user_id in (refreshed.doctor_user_id, refreshed.patient_user_id):
        publish_after_commit(session, user_topic(user_id), SESSION_UPDATED)
    return refreshed


async def record_presence(
    session: AsyncSession, row: PracticeSession, *, user_id: uuid.UUID, now: datetime
) -> PracticeSession:
    exam_code = await catalog.exam_code_by_id(session, row.exam_id) or ""
    updates: dict[str, datetime] = {}
    if user_id == row.doctor_user_id and row.doctor_joined_at is None:
        updates["doctor_joined_at"] = now
    if user_id == row.patient_user_id and row.patient_joined_at is None:
        updates["patient_joined_at"] = now
    if updates:
        await session.execute(update(PracticeSession).where(PracticeSession.id == row.id).values(**updates))
        row = await repository.session_by_id(session, row.id)  # type: ignore[assignment]
        assert row is not None

    doctor_in = row.doctor_joined_at is not None
    patient_in = row.patient_joined_at is not None
    if doctor_in and patient_in and row.preparation_started_at is None:
        durs = durations_for(exam_code)
        prep_end = now + timedelta(seconds=durs.preparation)
        await session.execute(
            update(PracticeSession)
            .where(PracticeSession.id == row.id)
            .values(
                preparation_started_at=now,
                current_phase="preparation",
                phase_ends_at=prep_end,
                status="active",
            )
        )
        row = await repository.session_by_id(session, row.id)  # type: ignore[assignment]
        assert row is not None
        for participant in (row.doctor_user_id, row.patient_user_id):
            publish_after_commit(session, user_topic(participant), SESSION_UPDATED)

    return await advance_phases_if_due(session, row, exam_code=exam_code, now=now)
