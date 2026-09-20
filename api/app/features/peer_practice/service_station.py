"""Station material exposed during a practice session."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain_material
from app.features.peer_practice.schemas import PracticeStationRead
from app.features.attempts.schemas_material import (
    CandidateScenarioRead, DoctorInformationRead, ManagementPlanRead, StationTeachingRead,
)
from app.features.attempts.schemas_roleplay import PatientRoleplayRead
from app.features.stations.models import Station, StationVersion
from app.features.stations.repository_library import versions_with_stations


async def station_read_for_version(
    session: AsyncSession, station_version_id: uuid.UUID | None, *,
    is_doctor: bool, reveal_review: bool,
) -> PracticeStationRead | None:
    if station_version_id is None:
        return None
    pairs = await versions_with_stations(session, None, [station_version_id])
    if not pairs:
        return None
    version, station = pairs[0]
    return _station_payload(station, version, is_doctor=is_doctor, reveal_review=reveal_review)


def _station_payload(station: Station, version: StationVersion, *, is_doctor: bool, reveal_review: bool) -> PracticeStationRead:
    content: dict[str, Any] = version.content or {}
    patient = domain_material.block(content, domain_material.PATIENT_BLOCKS)
    doctor = domain_material.block(content, ("doctor_information",))
    plan = domain_material.block(content, ("management_plan",))
    reading = domain_material.text(content.get("reading_brief") or doctor.get("reading_brief") or "")
    patient_script = domain_material.text(
        patient.get("patient_script") or patient.get("script") or content.get("patient_script") or ""
    )
    management = domain_material.text(plan.get("management_plan") or plan.get("plan") or "")
    scenario = domain_material.scenario(content)
    teaching = domain_material.teaching(content)
    actor = PatientRoleplayRead(
        **{key: domain_material.lines(patient.get(key)) for key in (
            "idea", "concerns", "expectation", "family_social_history", "past_med_history_allergies", "questions",
        )},
        **{key: domain_material.text(patient.get(key)) for key in (
            "patient_biodata", "gender", "opening_sentence", "expanded_history", "persona",
        )},
    ) if patient else None
    return PracticeStationRead(
        station_id=station.id,
        station_version_id=version.id,
        title=station.title,
        reading_brief=reading,
        patient_script=patient_script if not is_doctor or reveal_review else None,
        management_plan=management if reveal_review else None,
        doctor_information=DoctorInformationRead(**doctor) if doctor else None,
        patient_information=actor if not is_doctor or reveal_review else None,
        management=ManagementPlanRead(**plan) if plan and reveal_review else None,
        scenario=CandidateScenarioRead(**scenario) if scenario else None,
        teaching=StationTeachingRead(**teaching) if teaching and reveal_review else None,
    )
