"""What each side of a peer session may read of the station, by template audience.

`service_station._station_payload` used to duplicate the attempt material
readers' legacy field lists. It now projects the same `AudienceSectionRead`
shape `stations.service.audience_sections` builds for an attempt, gated on
role and phase rather than on a station's field names.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.peer_practice import service_station
from app.features.stations import repository as stations_repo
from app.features.stations import repository_templates as templates_repo
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

STRUCTURE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "doctor_information",
            "title": "Doctor information",
            "audience": "candidate",
            "blocks": [
                {"id": "task_instructions", "type": "text", "label": "Task", "role": "candidate_brief"}
            ],
        },
        {
            "id": "patient_information",
            "title": "Patient information",
            "audience": "patient",
            "blocks": [
                {"id": "persona", "type": "text", "label": "Persona", "role": "persona"},
                {"id": "idea", "type": "list", "label": "Idea", "role": "hidden"},
            ],
        },
        {
            "id": "management_plan",
            "title": "Management plan",
            "audience": "examiner",
            "blocks": [{"id": "explanation", "type": "text", "label": "Explanation", "role": "examiner"}],
        },
    ],
    "layout": {"persona": "patient"},
}

CONTENT = {
    "doctor_information": {"task_instructions": "Take a history from Mr Bello."},
    "patient_information": {"persona": "Anxious, talks quickly", "idea": ["Thinks it is indigestion"]},
    "management_plan": {"explanation": "Likely stable angina."},
}


async def _station_version(session: AsyncSession) -> uuid.UUID:
    exam = await ensure_exam(session, "sca")
    assert exam is not None
    template = await templates_repo.create_template(session, None, exam_id=exam.id, title="Consultation")
    template_version = await templates_repo.add_template_version(
        session, None, template_id=template.id, version=1, structure=STRUCTURE
    )
    await templates_repo.set_template_version_status(
        session, None, template_version.id, status="published", at=NOW, by=None
    )
    station = await stations_repo.create_station(session, None, exam_id=exam.id, title="Chest pain")
    version = await stations_repo.add_version(
        session,
        None,
        station_id=station.id,
        version=1,
        content=CONTENT,
        template_version_id=template_version.id,
    )
    await stations_repo.set_version_status(session, None, version.id, status="published", at=NOW, by=None)
    await session.flush()
    return version.id


async def test_the_doctor_reads_only_the_candidate_audience_before_the_debrief(
    db_session: AsyncSession,
) -> None:
    version_id = await _station_version(db_session)

    station = await service_station.station_read_for_version(
        db_session, version_id, is_doctor=True, reveal_review=False
    )

    assert station is not None
    assert {section["id"] if isinstance(section, dict) else section.id for section in station.sections} == {
        "doctor_information"
    }


async def test_the_patient_actor_reads_the_hidden_blocks_of_their_own_script(
    db_session: AsyncSession,
) -> None:
    version_id = await _station_version(db_session)

    station = await service_station.station_read_for_version(
        db_session, version_id, is_doctor=False, reveal_review=False
    )

    assert station is not None
    section_ids = {section.id for section in station.sections}
    assert section_ids == {"doctor_information", "patient_information"}
    patient_section = next(s for s in station.sections if s.id == "patient_information")
    block_ids = {block.id for block in patient_section.blocks}
    assert "idea" in block_ids  # hidden-role, and this is the actor playing it


async def test_the_debrief_reveals_the_examiner_audience_to_both(db_session: AsyncSession) -> None:
    version_id = await _station_version(db_session)

    doctor_view = await service_station.station_read_for_version(
        db_session, version_id, is_doctor=True, reveal_review=True
    )

    assert doctor_view is not None
    section_ids = {section.id for section in doctor_view.sections}
    assert section_ids == {"doctor_information", "patient_information", "management_plan"}
    plan = next(s for s in doctor_view.sections if s.id == "management_plan")
    assert plan.blocks[0].value == "Likely stable angina."
