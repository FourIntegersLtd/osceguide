"""Reads across every owner, for the staff who work on one station by id.

Split from `repository.py` at the file cap and by tenancy rule: everything
there takes `org_id` first because a caller is always somebody's member. The
console is nobody's member and may read any station for support, so this is
the one place a station is found by id alone. Reaching it is not the same as
being allowed to know what was found: each route decides that for itself, and
for an organisation's own station the answer is its administrators.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stations.models import Station, StationVersion


async def station_with_versions(
    session: AsyncSession, station_id: uuid.UUID
) -> tuple[Station, list[StationVersion]] | None:
    station = (await session.execute(select(Station).where(Station.id == station_id))).scalar_one_or_none()
    if station is None:
        return None
    versions = (
        await session.execute(
            select(StationVersion)
            .where(StationVersion.station_id == station_id)
            .order_by(StationVersion.version)
        )
    ).scalars()
    return station, list(versions)


async def versions_with_stations_any_owner(
    session: AsyncSession, version_ids: Collection[uuid.UUID]
) -> list[tuple[StationVersion, Station]]:
    """Several versions and their stations, whoever owns them."""
    if not version_ids:
        return []
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(StationVersion.id.in_(list(version_ids)))
    )
    return [(v, s) for v, s in (await session.execute(stmt)).all()]
