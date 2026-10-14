"""A published platform-library station for an exam, written directly."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations.models import Station, StationTemplate, StationTemplateVersion, StationVersion
from tests.support.catalog import ensure_exam


async def publish_library_station(
    db_session: AsyncSession, exam_code: str = "sca", *, title: str = "Library"
) -> uuid.UUID:
    """The exam (made if need be) with one published library station; returns the version id."""
    exam = await ensure_exam(db_session, exam_code)
    assert exam is not None
    station = Station(owner_kind="platform", org_id=None, exam_id=exam.id, title=title, status="published")
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(
        station_id=station.id,
        org_id=None,
        version=1,
        content={"patient_information": {"persona": "anxious"}},
        status="published",
    )
    db_session.add(version)
    await db_session.flush()
    station.current_version_id = version.id
    await db_session.flush()
    return version.id


async def bind_to_template(db_session: AsyncSession, version_id: uuid.UUID) -> None:
    """Publish a platform template and bind the station version to it."""
    template = StationTemplate(owner_kind="platform", org_id=None, title="Standard")
    db_session.add(template)
    await db_session.flush()
    template_version = StationTemplateVersion(
        owner_kind="platform", template_id=template.id, version=1, structure={}, status="published"
    )
    db_session.add(template_version)
    await db_session.flush()
    version = await db_session.get(StationVersion, version_id)
    assert version is not None
    version.template_version_id = template_version.id
    await db_session.flush()


async def add_unbound_station(
    db_session: AsyncSession, exam_code: str, *, org_id: uuid.UUID | None, status: str
) -> None:
    """A station (the platform's when `org_id` is None) whose current version has no template."""
    exam = await ensure_exam(db_session, exam_code)
    assert exam is not None
    station = Station(
        owner_kind="platform" if org_id is None else "org",
        org_id=org_id,
        exam_id=exam.id,
        title="Unbound",
        status=status,
    )
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(station_id=station.id, org_id=org_id, version=1, content={}, status=status)
    db_session.add(version)
    await db_session.flush()
    station.current_version_id = version.id
    await db_session.flush()
