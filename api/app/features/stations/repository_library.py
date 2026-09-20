"""Queries that join a version to its station.

Split from `repository.py` at the file cap. These are bulk reads for screens
that already hold a set of version ids, or for a re-index of the library.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import visible_to
from app.features.stations.models import Station, StationVersion


async def versions_with_stations(
    session: AsyncSession, org_id: uuid.UUID | None, version_ids: Sequence[uuid.UUID]
) -> list[tuple[StationVersion, Station]]:
    """Several versions and the stations that own them, in one query.

    Scoped like `version_for_attempt`: the platform library is everybody's, an
    org's own stations are only its own. A circuit mixes both, which is why a
    console asking for its slots' station titles asks here once rather than
    resolving each id through the station routes.
    """
    if not version_ids:
        return []
    owner = visible_to(Station, org_id)
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(StationVersion.id.in_(list(version_ids)), owner)
    )
    return [(v, s) for v, s in (await session.execute(stmt)).all()]


async def published_library_versions(
    session: AsyncSession, *, exam_id: uuid.UUID | None = None
) -> list[tuple[StationVersion, Station]]:
    """Every current, published platform-library version, with its station.

    The whole library at once rather than a page, because the only caller is a
    re-index that has to see all of it: a paged walk of a table being written
    to can miss a row or read one twice, and either leaves the index quietly
    wrong about material nobody will check.
    """
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(
            Station.owner_kind == "platform",
            Station.status == "published",
            StationVersion.status == "published",
            StationVersion.id == Station.current_version_id,
        )
    )
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    return [(v, s) for v, s in (await session.execute(stmt)).all()]
