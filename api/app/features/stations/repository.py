"""Storage for stations and their versions.

Every method takes `org_id` first, and `None` means the platform's own rows —
the library. Which ownership predicate each uses is the tenancy decision:
`owned_by` for a write, `visible_to` for a read that should also reach the
library. See `app.core.ownership`.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import owned_by, owner_kind_for, visible_to
from app.core.pagination import keyset_page
from app.features.stations.models import Station, StationVersion


async def create_station(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    exam_id: uuid.UUID,
    title: str,
) -> Station:
    """Create a new station shell, with no versions yet."""
    station = Station(owner_kind=owner_kind_for(org_id), org_id=org_id, exam_id=exam_id, title=title)
    session.add(station)
    await session.flush()
    await session.refresh(station)
    return station


async def add_version(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    station_id: uuid.UUID,
    version: int,
    content: dict[str, Any],
    template_version_id: uuid.UUID | None = None,
) -> StationVersion:
    """Add a new draft version to a station."""
    station_version = StationVersion(
        station_id=station_id,
        org_id=org_id,
        version=version,
        content=content,
        template_version_id=template_version_id,
    )
    session.add(station_version)
    await session.flush()
    await session.refresh(station_version)
    return station_version


async def station_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID
) -> Station | None:
    """One station this org owns, by id."""
    stmt = select(Station).where(owned_by(Station, org_id), Station.id == station_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def exists_by_id(session: AsyncSession, station_id: uuid.UUID) -> bool:
    """Whether a station carries this id at all, under any owner.

    Not org-scoped, and so not narrowing by org: a community comment names a
    station without knowing whose it is, and needs existence rather than
    ownership answered.
    """
    stmt = select(Station.id).where(Station.id == station_id)
    return (await session.execute(stmt)).first() is not None


async def versions_for_station(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID
) -> list[StationVersion]:
    """Every version of this station, oldest first."""
    stmt = (
        select(StationVersion)
        .where(owned_by(StationVersion, org_id), StationVersion.station_id == station_id)
        .order_by(StationVersion.version)
    )
    return list((await session.execute(stmt)).scalars())


async def version_by_number(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> StationVersion | None:
    """One version of this station, by its version number."""
    stmt = select(StationVersion).where(
        owned_by(StationVersion, org_id),
        StationVersion.station_id == station_id,
        StationVersion.version == version,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_version_content(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID, *, content: dict[str, Any]
) -> None:
    """Overwrite a draft version's content."""
    await session.execute(
        update(StationVersion)
        .where(owned_by(StationVersion, org_id), StationVersion.id == version_id)
        .values(content=content)
    )


async def set_version_status(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    version_id: uuid.UUID,
    *,
    status: str,
    at: datetime,
    by: uuid.UUID,
) -> None:
    """Move a version to `published` or `archived`, stamping who did it and when."""
    values: dict[str, Any] = {"status": status}
    if status == "published":
        values |= {"published_at": at, "published_by": by}
    elif status == "archived":
        values |= {"archived_at": at, "archived_by": by}
    await session.execute(
        update(StationVersion)
        .where(owned_by(StationVersion, org_id), StationVersion.id == version_id)
        .values(**values)
    )


async def set_current_version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, *, version_id: uuid.UUID
) -> None:
    """Point the station at its newly published version."""
    await session.execute(
        update(Station)
        .where(owned_by(Station, org_id), Station.id == station_id)
        .values(current_version_id=version_id, status="published")
    )


async def retire_station(session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID) -> None:
    """Take a station with no published version left out of use: archived, pointing at nothing."""
    await session.execute(
        update(Station)
        .where(owned_by(Station, org_id), Station.id == station_id)
        .values(current_version_id=None, status="archived")
    )


async def list_for_org(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
    search: str | None = None,
    include_archived: bool = False,
) -> tuple[list[Station], str | None]:
    """A page of this org's stations, newest first, optionally filtered by exam, title or status.

    Archived stations are left out by default — `include_archived` is the only way back in — since a
    list an author browses to keep working on is, by default, the stations still in use.
    """
    stmt = select(Station).where(owned_by(Station, org_id))
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    if search and search.strip():
        # Matched the same way the library's search is (`library_page`): a
        # title fragment, in SQL, so a term matches the whole catalogue rather
        # than only the page the screen had already walked.
        stmt = stmt.where(Station.title.ilike(f"%{search.strip()}%"))
    if not include_archived:
        stmt = stmt.where(Station.status != "archived")
    return await _station_page(session, stmt, limit=limit, cursor=cursor)


async def _station_page(
    session: AsyncSession, stmt: Select[Any], *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[Station], str | None]:
    """Apply the shared keyset pagination to a stations query, oldest first."""
    return await keyset_page(
        session,
        stmt,
        sort_col=Station.created_at,
        id_col=Station.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def version_for_attempt(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> tuple[StationVersion, Station] | None:
    """A version an attempt may run, with the station that owns it.

    Scoped deliberately: a platform library station (`org_id IS NULL`) is
    available to everyone, and an org's own station only to that org. Without
    the second half this would be a global lookup by id, which is the shape
    that leaks across tenants elsewhere in the legacy code.
    """
    owner = visible_to(Station, org_id)
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(StationVersion.id == version_id, owner)
    )
    pair = (await session.execute(stmt)).first()
    return (pair[0], pair[1]) if pair else None


async def count_for_org(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    """How many stations this org owns."""
    stmt = select(func.count()).select_from(Station).where(owned_by(Station, org_id))
    return int((await session.execute(stmt)).scalar_one())


async def count_platform_library(session: AsyncSession, exam_ids: list[uuid.UUID]) -> int:
    """Published library stations for the exams an organisation offers.

    What it may run without authoring anything, which is why the dashboard asks
    for it alongside `count_for_org`. Empty is a flat zero: `in_([])` matches
    nothing, and an organisation offering no exam has no library to draw on.
    """
    if not exam_ids:
        return 0
    stmt = (
        select(func.count())
        .select_from(Station)
        .where(
            Station.owner_kind == "platform",
            Station.status == "published",
            Station.exam_id.in_(exam_ids),
        )
    )
    return int((await session.execute(stmt)).scalar_one())


async def delete_version(session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID) -> None:
    """Remove one revision. The service refuses anything but a draft (T6)."""
    await session.execute(
        delete(StationVersion).where(owned_by(StationVersion, org_id), StationVersion.id == version_id)
    )


# --- Reads across every owner, for the staff who work on one station by id.


async def station_with_versions(
    session: AsyncSession, station_id: uuid.UUID
) -> tuple[Station, list[StationVersion]] | None:
    """A station and all its versions, regardless of owner, for staff working on it by id."""
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
    return [(version, station) for version, station in (await session.execute(stmt)).all()]


async def version_ids_matching_title(session: AsyncSession, search: str) -> list[uuid.UUID]:
    """Ids of every station version whose station's title contains `search`, case-insensitively.

    For another slice's list to filter on a station title without importing this slice's models.
    """
    stmt = (
        select(StationVersion.id)
        .join(Station, Station.id == StationVersion.station_id)
        .where(Station.title.ilike(f"%{search}%"))
    )
    return list((await session.execute(stmt)).scalars())
