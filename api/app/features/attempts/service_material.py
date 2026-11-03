"""What a candidate may read about a station they are sitting, or have sat.

The rule, in one sentence: the brief is theirs as soon as they have started, and the model answer is
theirs once the consultation is over. Everything else in the document — the patient's persona and
hidden history, the examiner's expected answers, the marking guidance — never leaves the server,
which is why this reads a station by its template's audiences (`stations.service.audience_sections`)
rather than passing `content` through.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Page
from app.core.schemas import AudienceSectionRead
from app.features.attempts import domain, domain_material, errors, repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import PatientRoleplayRead
from app.features.attempts.schemas_material import (
    AttemptBriefRead,
    AttemptHistoryItem,
    AttemptReviewRead,
    PatientIdentityRead,
)
from app.features.attempts.service_reads import _ensure_visible, _require
from app.features.catalog import service as catalog
from app.features.stations import service as stations_service
from app.features.stations import service_reads as stations

# Where a block carries the patient's identity, across the template's own
# vocabulary (`patient_biodata`, `gender`) and the legacy flat key the
# nested b2c documents used before there was a template at all.
_NAME_LINE_BLOCK_IDS = ("patient_biodata",)
_GENDER_BLOCK_IDS = ("gender",)


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
    candidate_sections = await stations_service.audience_sections(
        session,
        material.template_version_id,
        material.content,
        ("candidate",),
        station_id=material.station_id,
    )
    patient_sections = await stations_service.audience_sections(
        session, material.template_version_id, material.content, ("patient",), station_id=material.station_id
    )

    return AttemptBriefRead(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_code=exam_code,
        station_id=material.station_id,
        station_version_id=material.version_id,
        station_title=material.title,
        set_entry_id=attempt.set_entry_id,
        created_at=attempt.created_at,
        started_at=attempt.started_at,
        server_time=datetime.now(UTC),
        patient=_patient_identity(material.content, patient_sections),
        sections=candidate_sections,
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

    # The candidate's own brief again, plus every examiner section — the model
    # answer and the marking guidance — now that the consultation is over.
    sections = await stations_service.audience_sections(
        session,
        material.template_version_id,
        material.content,
        ("candidate", "examiner"),
        station_id=material.station_id,
    )

    return AttemptReviewRead(
        attempt_id=attempt.id,
        kind=attempt.kind,
        status=attempt.status,
        exam_code=exam_code,
        station_id=material.station_id,
        station_version_id=material.version_id,
        station_title=material.title,
        set_entry_id=attempt.set_entry_id,
        sections=sections,
    )


def _patient_identity(
    content: dict[str, Any], patient_sections: Sequence[AudienceSectionRead]
) -> PatientIdentityRead:
    """Who the candidate is about to speak to, for the consultation header.

    Read from the patient audience's own `persona`-role blocks first — a
    template names its biodata and gender blocks `patient_biodata` and
    `gender` (see `seeds/station-templates.json`) — and falls back to the flat
    `patient_gender` key every legacy document also carries, for a station
    with no template bound yet.
    """
    name_line: str | None = None
    gender: str | None = None
    for section in patient_sections:
        for block in section.blocks:
            if block.id in _NAME_LINE_BLOCK_IDS and name_line is None:
                name_line = domain_material.text(block.value)
            if block.id in _GENDER_BLOCK_IDS and gender is None:
                gender = domain_material.text(block.value)
    if gender is None:
        gender = domain_material.text(content.get("patient_gender"))
    return PatientIdentityRead(name_line=name_line, gender=gender)


async def list_history(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    cursor: dict[str, Any] | None,
    station_version_id: uuid.UUID | None = None,
    set_entry_id: uuid.UUID | None = None,
    search: str | None = None,
    transcribable_only: bool = False,
) -> Page[AttemptHistoryItem]:
    """What this person has sat, newest first, each row naming its station.

    `search` and `transcribable_only` are the two filters the transcripts
    screen used to apply after walking every page of this endpoint itself —
    see `repository.list_for_user`. `search` also matches an exam's code,
    resolved to ids here through catalog's own service rather than joining
    its table from this slice's repository.
    """
    matching_exam_ids = await catalog.exam_ids_matching_code(session, search) if search else None
    attempts, next_cursor = await repository.list_for_user(
        session,
        user_id,
        limit=limit,
        cursor=cursor,
        station_version_id=station_version_id,
        set_entry_id=set_entry_id,
        search=search,
        matching_exam_ids=matching_exam_ids,
        transcribable_only=transcribable_only,
    )
    marked = await transcripts.attempt_ids_with_results(session, [attempt.id for attempt in attempts])
    # Titles and exam codes in one query each rather than one per row: a page
    # of twenty attempts against the same station asked the same question
    # twenty times in the client the day this replaced.
    version_ids = [
        attempt.station_version_id for attempt in attempts if attempt.station_version_id is not None
    ]
    summaries = await stations.summaries_by_version_id(session, None, version_ids)
    codes = await catalog.exam_codes_by_id(session, [attempt.exam_id for attempt in attempts])

    history: list[AttemptHistoryItem] = []
    for attempt in attempts:
        # A debrief has no station of its own — it is about another attempt —
        # so a row with no version id is named by its kind rather than skipped.
        summary = summaries.get(attempt.station_version_id) if attempt.station_version_id else None
        history.append(
            AttemptHistoryItem(
                id=attempt.id,
                kind=attempt.kind,
                status=attempt.status,
                exam_code=codes.get(attempt.exam_id, ""),
                station_id=summary.station_id if summary else None,
                station_version_id=attempt.station_version_id,
                station_title=summary.title if summary else None,
                set_entry_id=attempt.set_entry_id,
                created_at=attempt.created_at,
                completed_at=attempt.completed_at,
                has_result=attempt.id in marked,
            )
        )
    return Page(items=history, next_cursor=next_cursor)


async def _material_for(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID, is_admin: bool
) -> tuple[Attempt, stations.VersionMaterial, str]:
    """The attempt, its station's material and its exam code, once the requester may see it."""
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


# --- Read only the actor's script, after the owning learner has finished.


async def read_roleplay(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID
) -> PatientRoleplayRead:
    """The patient's script, for the candidate to play back once their own attempt has finished.

    `include_hidden=True`: the actor needs the whole patient audience, including the ICE and the
    questions a template marks `hidden` — the material a candidate reading the brief or the review
    never sees, because it is how the patient is played, not what they are assessed on.
    """
    attempt, material, _ = await _material_for(session, attempt_id, requester_id=requester_id, is_admin=False)
    if not domain.is_reviewable(domain.Status(attempt.status)):
        raise errors.AttemptNotFinished()
    sections = await stations_service.audience_sections(
        session,
        material.template_version_id,
        material.content,
        ("patient",),
        station_id=material.station_id,
        include_hidden=True,
    )
    return PatientRoleplayRead(sections=sections)
