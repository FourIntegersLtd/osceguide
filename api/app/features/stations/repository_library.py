"""Queries against the platform's own half of the station table.

The library is the one body of stations that is nobody's — `owner_kind = 'platform'`,
`org_id IS NULL`. Every question asked of it is spelled the same way: narrow by exam or title, page
by the shared keyset cursor. The rest are the joins a bulk reader needs when it holds version ids
rather than stations.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import visible_to
from app.core.pagination import keyset_page
from app.features.stations.models import Station, StationVersion


async def library_page(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    search: str | None = None,
) -> tuple[list[Station], str | None]:
    """A page of the published library, narrowed by exam and by title.

    `search` belongs in SQL rather than in whoever asked: applying a filter to an already-fetched
    page can only ever match the rows that page contained.
    """
    stmt = select(Station).where(Station.owner_kind == "platform", Station.status == "published")
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    if search and search.strip():
        # Matched like the console's other title filters, including its LIKE
        # wildcards: a `%` typed into a search box widens the query here too.
        stmt = stmt.where(Station.title.ilike(f"%{search.strip()}%"))
    return await keyset_page(
        session,
        stmt,
        sort_col=Station.created_at,
        id_col=Station.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def library_station(
    session: AsyncSession, station_id: uuid.UUID
) -> tuple[Station, StationVersion] | None:
    """One published library station with the version it currently points at.

    The join is the tenancy rule as well as the shape of the answer: a draft,
    an archived-never-published row, and any organisation's own station are all
    absent from the library, and this returns None for each rather than saying
    which. A station id is something a stranger may guess at, and the library
    answers only for the library's own.
    """
    stmt = (
        select(Station, StationVersion)
        .join(StationVersion, StationVersion.id == Station.current_version_id)
        .where(
            Station.id == station_id,
            Station.owner_kind == "platform",
            Station.status == "published",
        )
    )
    pair = (await session.execute(stmt)).first()
    return (pair[0], pair[1]) if pair else None


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
    return [(version, station) for version, station in (await session.execute(stmt)).all()]


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
    return [(version, station) for version, station in (await session.execute(stmt)).all()]
