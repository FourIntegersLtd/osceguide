"""A published platform-library station for an exam, written directly."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations.models import Station, StationVersion
from tests.support.catalog import ensure_exam


async def publish_library_station(db_session: AsyncSession, exam_code: str = "sca") -> uuid.UUID:
    """The exam (made if need be) with one published library station; returns the version id."""
    exam = await ensure_exam(db_session, exam_code)
    assert exam is not None
    station = Station(
        owner_kind="platform", org_id=None, exam_id=exam.id, title="Library", status="published"
    )
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
