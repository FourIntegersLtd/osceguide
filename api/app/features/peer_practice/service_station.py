"""Station material exposed during a practice session."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.peer_practice.models import PracticeSession
from app.features.peer_practice.schemas import (
    PracticeCandidateScenarioRead,
    PracticeDoctorInformationRead,
    PracticeManagementPlanRead,
    PracticePatientRoleplayRead,
    PracticeSessionRead,
    PracticeStationRead,
    PracticeStationTeachingRead,
)
from app.features.stations import service_reads as stations

_PATIENT_KEYS = ("patient_information", "patient_info")
_SCENARIO_KEYS = (
    "station_type",
    "clinical_scenario_title",
    "clinical_scenario",
    "radiograph_image_url",
    "additional_image_urls",
    "background_overview",
    "patient_list_for_candidate",
    "duration_minutes",
)
_TEACHING_KEYS = (
    "key_concerns",
    "history_overview",
    "examination_overview",
    "investigations_overview",
    "management_overview",
    "interview_questions",
    "references",
    "examiner_additional_info",
    "suggested_order_overview",
    "suggested_order",
    "communication_themes",
    "consent_approach",
    "breaking_bad_news_framework",
    "professional_conduct_topics",
    "key_learning_points",
    "portfolio_themes",
)


def _block(content: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    for key in keys:
        value = content.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    t = str(value).strip()
    return t or None


def _lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Mapping):
        return [str(item).strip() for item in value.values() if str(item).strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


async def session_read(
    session: AsyncSession, row: PracticeSession, *, viewer_id: uuid.UUID
) -> PracticeSessionRead:
    """Build the full session read payload, delegating station resolution here."""
    from app.features.catalog import service as catalog
    from app.features.peer_practice import domain

    code = await catalog.exam_code_by_id(session, row.exam_id)
    is_doctor = row.doctor_user_id == viewer_id
    partner_joined = bool(row.preparation_started_at)
    station = await station_read_for_version(
        session,
        row.station_version_id,
        is_doctor=is_doctor,
        reveal_review=row.current_phase in {"debrief", "completed"} or row.status == "ended",
    )
    return PracticeSessionRead(
        id=row.id,
        exam_code=code or "",
        my_role=str(domain.Role.DOCTOR if is_doctor else domain.Role.PATIENT),
        partner_user_id=row.patient_user_id if is_doctor else row.doctor_user_id,
        room_name=row.room_name,
        status=row.status,
        current_phase=row.current_phase,
        phase_ends_at=row.phase_ends_at,
        preparation_started_at=row.preparation_started_at,
        doctor_joined_at=row.doctor_joined_at,
        patient_joined_at=row.patient_joined_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
        end_reason=row.end_reason,
        station=station,
        partner_joined=partner_joined,
        doctor_attempt_id=row.doctor_attempt_id if is_doctor else None,
        feedback_state=_feedback_state(row) if is_doctor else "none",
    )


def _feedback_state(row: PracticeSession) -> str:
    """What the doctor can be told about their marking, in one word.

    Derived from the recording rather than stored: the states are already
    written on the row by the recorder and the job, and a second field saying
    the same thing is a second field to get wrong.
    """
    if row.doctor_attempt_id is not None:
        return "ready"
    if row.recording_state == "failed":
        return "failed"
    if row.recording_state == "none":
        return "none"
    return "pending"


async def station_read_for_version(
    session: AsyncSession,
    station_version_id: uuid.UUID | None,
    *,
    is_doctor: bool,
    reveal_review: bool,
) -> PracticeStationRead | None:
    if station_version_id is None:
        return None
    mat = await stations.version_material(session, None, station_version_id)
    if mat is None:
        return None
    return _station_payload(mat, is_doctor=is_doctor, reveal_review=reveal_review)


def _station_payload(
    mat: stations.VersionMaterial, *, is_doctor: bool, reveal_review: bool
) -> PracticeStationRead:
    content: dict[str, Any] = mat.content or {}
    patient = _block(content, _PATIENT_KEYS)
    doctor = _block(content, ("doctor_information",))
    plan = _block(content, ("management_plan",))
    reading = _text(content.get("reading_brief") or doctor.get("reading_brief") or "")
    patient_script = _text(
        patient.get("patient_script") or patient.get("script") or content.get("patient_script") or ""
    )
    management = _text(plan.get("management_plan") or plan.get("plan") or "")
    scenario = {key: content[key] for key in _SCENARIO_KEYS if key in content} or None
    teaching = {key: content[key] for key in _TEACHING_KEYS if key in content}
    actor = (
        PracticePatientRoleplayRead(
            **{
                key: _lines(patient.get(key))
                for key in (
                    "idea",
                    "concerns",
                    "expectation",
                    "family_social_history",
                    "past_med_history_allergies",
                    "questions",
                )
            },
            **{
                key: _text(patient.get(key))
                for key in (
                    "patient_biodata",
                    "gender",
                    "opening_sentence",
                    "expanded_history",
                    "persona",
                )
            },
        )
        if patient
        else None
    )
    return PracticeStationRead(
        station_id=mat.station_id,
        station_version_id=mat.version_id,
        title=mat.title,
        reading_brief=reading,
        patient_script=patient_script if not is_doctor or reveal_review else None,
        management_plan=management if reveal_review else None,
        doctor_information=PracticeDoctorInformationRead(**doctor) if doctor else None,
        patient_information=actor if not is_doctor or reveal_review else None,
        management=PracticeManagementPlanRead(**plan) if plan and reveal_review else None,
        scenario=PracticeCandidateScenarioRead(**scenario) if scenario else None,
        teaching=PracticeStationTeachingRead(**teaching) if teaching and reveal_review else None,
    )
