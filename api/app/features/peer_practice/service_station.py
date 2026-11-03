"""Station material exposed during a practice session."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.peer_practice.models import PracticeSession
from app.features.peer_practice.schemas import PracticeSessionRead, PracticeStationRead
from app.features.stations import service as stations_service
from app.features.stations import service_reads as stations


async def session_read(
    session: AsyncSession, practice_session: PracticeSession, *, viewer_id: uuid.UUID
) -> PracticeSessionRead:
    """Build the full session read payload, delegating station resolution here."""
    from app.features.catalog import service as catalog
    from app.features.peer_practice import domain, repository

    code = await catalog.exam_code_by_id(session, practice_session.exam_id)
    is_doctor = practice_session.doctor_user_id == viewer_id
    partner_joined = bool(practice_session.preparation_started_at)
    station = await station_read_for_version(
        session,
        practice_session.station_version_id,
        is_doctor=is_doctor,
        reveal_review=practice_session.current_phase in {"debrief", "completed"}
        or practice_session.status == "ended",
    )
    my_accepted_at = (
        practice_session.doctor_accepted_at if is_doctor else practice_session.patient_accepted_at
    )
    partner_accepted_at = (
        practice_session.patient_accepted_at if is_doctor else practice_session.doctor_accepted_at
    )
    requeued_entry_id: uuid.UUID | None = None
    if (
        practice_session.status == "ended"
        and practice_session.end_reason in {"declined", "no_response"}
        and my_accepted_at is not None
    ):
        # This pairing ended without the viewer's say-so while they had
        # already accepted it, which is exactly when `service_match` puts them
        # back in the queue. Read back rather than threaded through as a
        # parameter: any live queue place answers "was I requeued", without
        # the ended session needing to remember one of its own.
        live_entry = await repository.live_entry(session, viewer_id, practice_session.exam_id)
        requeued_entry_id = live_entry.id if live_entry is not None else None
    return PracticeSessionRead(
        id=practice_session.id,
        exam_code=code or "",
        my_role=str(domain.Role.DOCTOR if is_doctor else domain.Role.PATIENT),
        partner_user_id=practice_session.patient_user_id if is_doctor else practice_session.doctor_user_id,
        room_name=practice_session.room_name,
        status=practice_session.status,
        current_phase=practice_session.current_phase,
        phase_ends_at=practice_session.phase_ends_at,
        preparation_started_at=practice_session.preparation_started_at,
        doctor_joined_at=practice_session.doctor_joined_at,
        patient_joined_at=practice_session.patient_joined_at,
        started_at=practice_session.started_at,
        ended_at=practice_session.ended_at,
        end_reason=practice_session.end_reason,
        station=station,
        partner_joined=partner_joined,
        doctor_attempt_id=practice_session.doctor_attempt_id if is_doctor else None,
        feedback_state=_feedback_state(practice_session) if is_doctor else "none",
        accept_expires_at=practice_session.accept_expires_at
        if practice_session.status == "pending_accept"
        else None,
        my_accepted=my_accepted_at is not None,
        partner_accepted=partner_accepted_at is not None,
        requeued_entry_id=requeued_entry_id,
    )


def _feedback_state(practice_session: PracticeSession) -> str:
    """What the doctor can be told about their marking, in one word.

    Derived from the recording rather than stored: the states are already
    written on the session by the recorder and the job, and a second field saying
    the same thing is a second field to get wrong.
    """
    if practice_session.doctor_attempt_id is not None:
        return "ready"
    if practice_session.recording_state == "failed":
        return "failed"
    if practice_session.recording_state == "none":
        return "none"
    return "pending"


async def station_read_for_version(
    session: AsyncSession,
    station_version_id: uuid.UUID | None,
    *,
    is_doctor: bool,
    reveal_review: bool,
) -> PracticeStationRead | None:
    """The station material for one version, shaped for this viewer's role and phase.

    `None` when there is no version set, or it has no material.
    """
    if station_version_id is None:
        return None
    mat = await stations.version_material(session, None, station_version_id)
    if mat is None:
        return None
    return await _station_payload(session, mat, is_doctor=is_doctor, reveal_review=reveal_review)


async def _station_payload(
    session: AsyncSession, mat: stations.VersionMaterial, *, is_doctor: bool, reveal_review: bool
) -> PracticeStationRead:
    """Shape one station's template-audience sections into the wire read model.

    The candidate audience is always visible — it is the doctor's own brief.
    The patient audience, hidden blocks included, is the actor's script: read
    by whoever is not playing the doctor, or by the doctor too once the
    debrief has revealed it. The examiner audience — the model answer and the
    marking guidance — is read by neither until `reveal_review`, the same
    moment an attempt's own review opens.
    """
    audiences = ["candidate"]
    include_hidden = not is_doctor
    if reveal_review:
        audiences.extend(["patient", "examiner"])
        include_hidden = True
    elif not is_doctor:
        audiences.append("patient")
    sections = await stations_service.audience_sections(
        session,
        mat.template_version_id,
        mat.content,
        tuple(audiences),
        station_id=mat.station_id,
        include_hidden=include_hidden,
    )
    return PracticeStationRead(
        station_id=mat.station_id,
        station_version_id=mat.version_id,
        title=mat.title,
        sections=sections,
    )
