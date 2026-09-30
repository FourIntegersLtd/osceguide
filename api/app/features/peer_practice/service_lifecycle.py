"""Presence, phased timing, and marketplace runtime sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_after_commit, user_topic
from app.core.ports import RoomRecorder
from app.features.catalog import service as catalog
from app.features.peer_practice import domain, repository_sessions, service_recording
from app.features.peer_practice.models import PracticeSession
from app.features.peer_practice.station_pick import pick_station_version_id
from app.features.peer_practice.timers import durations_for

SESSION_UPDATED = "practice.session_updated"


async def roles_for_peer_participants(
    session: AsyncSession, owner_id: uuid.UUID, claimer_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """Doctor and patient user ids for a booked pair."""
    histories = []
    for user_id in (owner_id, claimer_id):
        history = await repository_sessions.history_for(session, user_id)
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
    """Start a practice session for a marketplace-booked pair, assigning doctor and patient roles.

    Called from the marketplace slice once a booking is claimed. Its name and
    parameters are a contract with that caller and must not change here.
    """
    doctor_id, patient_id = await roles_for_peer_participants(session, owner_user_id, claimer_user_id)
    station_id = await pick_station_version_id(session, exam_id=exam_id, doctor_user_id=doctor_id)
    practice = await repository_sessions.create_session(
        session,
        exam_id=exam_id,
        doctor_user_id=doctor_id,
        patient_user_id=patient_id,
        station_version_id=station_id,
        peer_session_id=peer_session_id,
    )
    await repository_sessions.set_room(session, practice.id, room_name=f"practice_{practice.id}")
    await repository_sessions.record_role(session, doctor_id, role=str(domain.Role.DOCTOR))
    await repository_sessions.record_role(session, patient_id, role=str(domain.Role.PATIENT))
    return practice


async def advance_phases_if_due(
    session: AsyncSession,
    practice_session: PracticeSession,
    *,
    exam_code: str,
    now: datetime,
    recorder: RoomRecorder | None = None,
) -> PracticeSession:
    """Move the clock on, recording the consultation for as long as it lasts.

    `recorder` is threaded rather than built inside `service_recording` so a
    test can wire a fake the way every other port is wired here. Production
    passes nothing and the real Egress adapter is built on demand.
    """
    if (
        practice_session.status == "ended"
        or practice_session.current_phase is None
        or practice_session.phase_ends_at is None
    ):
        return practice_session
    if now < practice_session.phase_ends_at:
        return practice_session
    durs = durations_for(exam_code)
    next_phase: str | None = None
    next_end: datetime | None = None
    started_at: datetime | None = None
    if practice_session.current_phase == "preparation":
        next_phase = "consultation"
        next_end = now + timedelta(seconds=durs.consultation)
        started_at = now
    elif practice_session.current_phase == "consultation":
        next_phase = "debrief"
        next_end = now + timedelta(seconds=durs.debrief)
        started_at = practice_session.started_at
    elif practice_session.current_phase == "debrief":
        next_phase = "completed"
        next_end = None
        started_at = practice_session.started_at
    else:
        return practice_session
    values: dict[str, object] = {"current_phase": next_phase, "phase_ends_at": next_end}
    if practice_session.current_phase == "preparation":
        values["started_at"] = started_at
    if next_phase == "completed":
        values["status"] = "ended"
        values["ended_at"] = now
        values["end_reason"] = "phases_complete"
    if next_phase == "consultation":
        # Recording starts here rather than when the pair were matched: the
        # preparation phase is somebody reading a brief alone, and there is
        # nothing in it to mark.
        await service_recording.start_recording(
            session, practice_session, exam_code=exam_code, recorder=recorder
        )
    elif practice_session.current_phase == "consultation":
        await service_recording.stop_recording_and_queue(
            session, practice_session, now=now, recorder=recorder
        )
    await repository_sessions.advance_phase(session, practice_session.id, values=values)
    refreshed = await repository_sessions.session_by_id(session, practice_session.id)
    assert refreshed is not None
    for user_id in (refreshed.doctor_user_id, refreshed.patient_user_id):
        publish_after_commit(session, user_topic(user_id), SESSION_UPDATED, {"session_id": str(refreshed.id)})
    return refreshed


async def record_presence(
    session: AsyncSession,
    practice_session: PracticeSession,
    *,
    user_id: uuid.UUID,
    now: datetime,
    recorder: RoomRecorder | None = None,
) -> PracticeSession:
    """Mark one participant present, starting preparation once both have joined.

    Also advances the phase clock if it is already due, so a heartbeat that
    arrives late does double duty rather than waiting for the next one.
    """
    exam_code = await catalog.exam_code_by_id(session, practice_session.exam_id) or ""
    updates: dict[str, datetime] = {}
    if user_id == practice_session.doctor_user_id and practice_session.doctor_joined_at is None:
        updates["doctor_joined_at"] = now
    if user_id == practice_session.patient_user_id and practice_session.patient_joined_at is None:
        updates["patient_joined_at"] = now
    if updates:
        await repository_sessions.advance_phase(session, practice_session.id, values=updates)
        refreshed = await repository_sessions.session_by_id(session, practice_session.id)
        assert refreshed is not None
        practice_session = refreshed

    doctor_in = practice_session.doctor_joined_at is not None
    patient_in = practice_session.patient_joined_at is not None
    if doctor_in and patient_in and practice_session.preparation_started_at is None:
        durs = durations_for(exam_code)
        prep_end = now + timedelta(seconds=durs.preparation)
        await repository_sessions.advance_phase(
            session,
            practice_session.id,
            values={
                "preparation_started_at": now,
                "current_phase": "preparation",
                "phase_ends_at": prep_end,
                "status": "active",
            },
        )
        refreshed = await repository_sessions.session_by_id(session, practice_session.id)
        assert refreshed is not None
        practice_session = refreshed
        for participant in (practice_session.doctor_user_id, practice_session.patient_user_id):
            publish_after_commit(
                session, user_topic(participant), SESSION_UPDATED, {"session_id": str(practice_session.id)}
            )

    return await advance_phases_if_due(
        session, practice_session, exam_code=exam_code, now=now, recorder=recorder
    )
