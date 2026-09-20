"""Loading the consumer station library.

Idempotent on `station_versions.content->>'station_id'`, which the transform
always writes. There is no other natural key: a title is not unique, and two
exams legitimately have a station called "Chest pain".
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.models import Exam
from app.features.stations.models import Station, StationVersion
from app.migration.report import LoadReport
from app.migration.stations import MigratedStation


async def _existing_by_legacy_id(session: AsyncSession) -> dict[str, uuid.UUID]:
    rows = await session.execute(
        select(StationVersion.content["station_id"].astext, StationVersion.id).where(
            StationVersion.content["station_id"].astext.isnot(None)
        )
    )
    return {str(legacy): version_id for legacy, version_id in rows.all() if legacy}


async def load_stations(
    session: AsyncSession,
    stations: Sequence[MigratedStation],
    *,
    now: datetime | None = None,
) -> tuple[LoadReport, dict[str, uuid.UUID]]:
    """Load library stations. Returns the report and legacy id -> version id."""
    report = LoadReport()
    at = now or datetime.now(UTC)

    exam_rows = await session.execute(select(Exam.code, Exam.id))
    exams = {str(code).lower(): exam_id for code, exam_id in exam_rows.all()}
    by_legacy_id = await _existing_by_legacy_id(session)

    for station in stations:
        if station.legacy_id in by_legacy_id:
            report.stations_existing += 1
            continue

        exam_id = exams.get(station.exam_code)
        if exam_id is None:
            report.problem(
                f"station {station.legacy_id}: exam {station.exam_code!r} is not in this database; "
                "run alembic upgrade head so consumer exams exist"
            )
            continue

        row = Station(
            owner_kind="platform",
            org_id=None,
            exam_id=exam_id,
            title=station.title,
            status="published",
        )
        session.add(row)
        await session.flush()

        version = StationVersion(
            station_id=row.id,
            org_id=None,
            version=1,
            content=station.content,
            status="published",
            published_at=station.created_at or at,
        )
        session.add(version)
        await session.flush()

        row.current_version_id = version.id
        by_legacy_id[station.legacy_id] = version.id
        report.stations_created += 1

    return report, by_legacy_id
