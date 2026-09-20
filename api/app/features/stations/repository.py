"""Storage for stations and their versions.

Every method takes `org_id` first, and `None` means the platform's own rows —
the library. Which ownership predicate each uses is the tenancy decision:
`owned_by` for a write, `visible_to` for a read that should also reach the
library. See `app.core.ownership`.
"""

from __future__ import annotations

import uuid
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
    row = StationVersion(
        station_id=station_id,
        org_id=org_id,
        version=version,
        content=content,
        template_version_id=template_version_id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def station_by_id(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID
) -> Station | None:
    stmt = select(Station).where(owned_by(Station, org_id), Station.id == station_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def versions_for_station(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID
) -> list[StationVersion]:
    stmt = (
        select(StationVersion)
        .where(owned_by(StationVersion, org_id), StationVersion.station_id == station_id)
        .order_by(StationVersion.version)
    )
    return list((await session.execute(stmt)).scalars())


async def version_by_number(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> StationVersion | None:
    stmt = select(StationVersion).where(
        owned_by(StationVersion, org_id),
        StationVersion.station_id == station_id,
        StationVersion.version == version,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_version_content(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID, *, content: dict[str, Any]
) -> None:
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
    await session.execute(
        update(Station)
        .where(owned_by(Station, org_id), Station.id == station_id)
        .values(current_version_id=version_id, status="published")
    )


async def list_for_org(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
) -> tuple[list[Station], str | None]:
    stmt = select(Station).where(owned_by(Station, org_id))
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    return await _station_page(session, stmt, limit=limit, cursor=cursor)


async def versions_by_ids(
    session: AsyncSession, version_ids: list[uuid.UUID]
) -> dict[uuid.UUID, StationVersion]:
    if not version_ids:
        return {}
    stmt = select(StationVersion).where(StationVersion.id.in_(version_ids))
    rows = (await session.execute(stmt)).scalars().all()
    return {row.id: row for row in rows}


async def list_platform_library(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
) -> tuple[list[Station], str | None]:
    """The library every organisation can draw on. Deliberately not org-scoped."""
    stmt = select(Station).where(Station.owner_kind == "platform", Station.status == "published")
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    return await _station_page(session, stmt, limit=limit, cursor=cursor)


async def _station_page(
    session: AsyncSession, stmt: Select[Any], *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[Station], str | None]:
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
    row = (await session.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def count_for_org(session: AsyncSession, org_id: uuid.UUID | None) -> int:
    stmt = select(func.count()).select_from(Station).where(owned_by(Station, org_id))
    return int((await session.execute(stmt)).scalar_one())


async def delete_version(session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID) -> None:
    """Remove one revision. The service refuses anything but a draft (T6)."""
    await session.execute(
        delete(StationVersion).where(owned_by(StationVersion, org_id), StationVersion.id == version_id)
    )
