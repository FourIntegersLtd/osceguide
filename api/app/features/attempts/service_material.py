"""What a candidate may read about a station they are sitting, or have sat.

The rule, in one sentence: the brief is theirs as soon as they have started, and the model answer is
theirs once the consultation is over. Everything else in the document — the patient's persona and
hidden history, the examiner's expected answers, the marking guidance — never leaves the server,
which is why this reads named blocks out of `content` rather than passing it through.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page
from app.features.attempts import domain, domain_material, errors, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import PatientRoleplayRead
from app.features.attempts.schemas_material import (
    AttemptBriefRead,
    AttemptHistoryItem,
    AttemptReviewRead,
    CandidateScenarioRead,
    DoctorInformationRead,
    ManagementPlanRead,
    PatientIdentityRead,
    PatientReviewRead,
    StationTeachingRead,
)
from app.features.attempts.service_reads import _ensure_visible, _require
from app.features.catalog import service as catalog
from app.features.stations import service_reads as stations


async def read_brief(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> AttemptBriefRead:
    """The candidate's brief for an attempt they have started.

    Readable from `created`: the attempt is created when the station is opened
    and the reading period is the first thing that happens, so waiting for
    `running` would mean there was nothing to read until the patient had
    already been dispatched.
    """
    attempt, material, exam_code = await _material_for(
        session, attempt_id, requester_id=requester_id, is_admin=is_admin
    )
    content = material.content
    patient = domain_material.block(content, domain_material.PATIENT_BLOCKS)
    doctor = domain_material.block(content, ("doctor_information",))

    return AttemptBriefRead(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_code=exam_code,
        station_id=material.station_id,
        station_version_id=material.version_id,
        station_title=material.title,
        set_entry_id=attempt.set_entry_id,
        patient=PatientIdentityRead(
            name_line=domain_material.text(doctor.get("patient_biodata") or patient.get("patient_biodata")),
            gender=domain_material.text(patient.get("gender") or content.get("patient_gender")),
        ),
        doctor_information=DoctorInformationRead(**doctor) if doctor else None,
        scenario=_scenario_read(content),
    )


async def read_review(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> AttemptReviewRead:
    """The model answer, once there is a consultation to compare it against."""
    attempt, material, exam_code = await _material_for(
        session, attempt_id, requester_id=requester_id, is_admin=is_admin
    )
    if not domain.is_reviewable(domain.Status(attempt.status)):
        raise errors.AttemptNotFinished()

    content = material.content
    patient = domain_material.block(content, domain_material.PATIENT_BLOCKS)
    plan = domain_material.block(content, ("management_plan",))
    teaching = domain_material.teaching(content)

    return AttemptReviewRead(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_code=exam_code,
        station_id=material.station_id,
        station_version_id=material.version_id,
        station_title=material.title,
        set_entry_id=attempt.set_entry_id,
        patient_information=(
            PatientReviewRead(
                patient_biodata=domain_material.text(patient.get("patient_biodata")),
                gender=domain_material.text(patient.get("gender")),
                idea=domain_material.lines(patient.get("idea")),
                concerns=domain_material.lines(patient.get("concerns")),
                expectation=domain_material.lines(patient.get("expectation")),
            )
            if patient
            else None
        ),
        management_plan=ManagementPlanRead(**plan) if plan else None,
        scenario=_scenario_read(content),
        teaching=StationTeachingRead(**teaching) if teaching else None,
    )


async def list_history(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    cursor: dict[str, Any] | None,
    station_version_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
) -> Page[AttemptHistoryItem]:
    """What this person has sat, newest first, each row naming its station."""
    rows, next_cursor = await repository.list_for_user(
        session,
        user_id,
        limit=limit,
        cursor=cursor,
        station_version_id=station_version_id,
        set_entry_id=set_entry_id,
    )
    marked = await transcripts.attempt_ids_with_results(session, [row.id for row in rows])
    # Titles and exam codes in one query each rather than one per row: a page
    # of twenty attempts against the same station asked the same question
    # twenty times in the client the day this replaced.
    version_ids = [row.station_version_id for row in rows if row.station_version_id is not None]
    summaries = await stations.summaries_by_version_id(session, None, version_ids)
    codes = await catalog.exam_codes_by_id(session, [row.exam_id for row in rows])

    items: list[AttemptHistoryItem] = []
    for row in rows:
        # A debrief has no station of its own — it is about another attempt —
        # so a row with no version id is named by its kind rather than skipped.
        summary = summaries.get(row.station_version_id) if row.station_version_id else None
        items.append(
            AttemptHistoryItem(
                id=row.id,
                kind=row.kind,
                status=row.status,
                exam_code=codes.get(row.exam_id, ""),
                station_id=summary.station_id if summary else None,
                station_version_id=row.station_version_id,
                station_title=summary.title if summary else None,
                set_entry_id=row.set_entry_id,
                created_at=row.created_at,
                completed_at=row.completed_at,
                has_result=row.id in marked,
            )
        )
    return Page(items=items, next_cursor=next_cursor)


async def _material_for(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> tuple[Attempt, stations.VersionMaterial, str]:
    attempt = await _require(session, attempt_id)
    _ensure_visible(attempt, requester_id=requester_id, is_admin=is_admin)
    if attempt.station_version_id is None:
        raise errors.AttemptNotReady("This attempt has no station, so there is nothing to read.")

    material = await stations.version_material(session, attempt.org_id, attempt.station_version_id)
    if material is None:
        # The station was deleted out from under a recorded attempt. Reported
        # as "no such attempt material" rather than pretending to an empty
        # brief, which would read as a station with nothing written in it.
        raise errors.AttemptNotReady("The station behind this attempt is no longer readable.")

    return attempt, material, await catalog.exam_code_by_id(session, attempt.exam_id) or ""


def _scenario_read(content: Mapping[str, Any]) -> CandidateScenarioRead | None:
    present = domain_material.scenario(content)
    return CandidateScenarioRead(**present) if present else None


# --- Read only the actor's script, after the owning learner has finished.


async def read_roleplay(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID
) -> PatientRoleplayRead:
    attempt, material, _ = await _material_for(session, attempt_id, requester_id=requester_id, is_admin=False)
    if not domain.is_reviewable(domain.Status(attempt.status)):
        raise errors.AttemptNotFinished()
    patient = domain_material.block(material.content, domain_material.PATIENT_BLOCKS)
    return PatientRoleplayRead(
        idea=domain_material.lines(patient.get("idea")),
        concerns=domain_material.lines(patient.get("concerns")),
        expectation=domain_material.lines(patient.get("expectation")),
        family_social_history=domain_material.lines(patient.get("family_social_history")),
        past_med_history_allergies=domain_material.lines(patient.get("past_med_history_allergies")),
        questions=domain_material.lines(patient.get("questions")),
        patient_biodata=domain_material.text(patient.get("patient_biodata")),
        gender=domain_material.text(patient.get("gender")),
        opening_sentence=domain_material.text(patient.get("opening_sentence")),
        expanded_history=domain_material.text(patient.get("expanded_history")),
        persona=domain_material.text(patient.get("persona")),
    )
