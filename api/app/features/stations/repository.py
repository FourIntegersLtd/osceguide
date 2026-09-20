"""Storage for stations and their versions.

Org-scoped methods take `org_id` first. The platform library has no org, so the
methods that reach it say so in their names rather than passing None and hoping
the caller meant it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.stations.models import FeedbackTemplateVersion, Station, StationVersion


async def create_station(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    *,
    exam_id: uuid.UUID,
    title: str,
    owner_kind: str = "org",
) -> Station:
    station = Station(owner_kind=owner_kind, org_id=org_id, exam_id=exam_id, title=title)
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
) -> StationVersion:
    row = StationVersion(station_id=station_id, org_id=org_id, version=version, content=content)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def station_by_id(session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID) -> Station | None:
    stmt = select(Station).where(Station.org_id == org_id, Station.id == station_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def versions_for_station(
    session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID
) -> list[StationVersion]:
    stmt = (
        select(StationVersion)
        .where(StationVersion.org_id == org_id, StationVersion.station_id == station_id)
        .order_by(StationVersion.version)
    )
    return list((await session.execute(stmt)).scalars())


async def version_by_number(
    session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID, version: int
) -> StationVersion | None:
    stmt = select(StationVersion).where(
        StationVersion.org_id == org_id,
        StationVersion.station_id == station_id,
        StationVersion.version == version,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def set_version_content(
    session: AsyncSession, org_id: uuid.UUID, version_id: uuid.UUID, *, content: dict[str, Any]
) -> None:
    await session.execute(
        update(StationVersion)
        .where(StationVersion.org_id == org_id, StationVersion.id == version_id)
        .values(content=content)
    )


async def set_version_status(
    session: AsyncSession,
    org_id: uuid.UUID,
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
        .where(StationVersion.org_id == org_id, StationVersion.id == version_id)
        .values(**values)
    )


async def set_current_version(
    session: AsyncSession, org_id: uuid.UUID, station_id: uuid.UUID, *, version_id: uuid.UUID
) -> None:
    await session.execute(
        update(Station)
        .where(Station.org_id == org_id, Station.id == station_id)
        .values(current_version_id=version_id, status="published")
    )


async def list_for_org(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    exam_id: uuid.UUID | None = None,
) -> tuple[list[Station], str | None]:
    stmt = select(Station).where(Station.org_id == org_id)
    if exam_id is not None:
        stmt = stmt.where(Station.exam_id == exam_id)
    if cursor:
        stmt = stmt.where(Station.created_at > datetime.fromisoformat(cursor["t"]))
    rows = list(
        (await session.execute(stmt.order_by(Station.created_at, Station.id).limit(limit + 1))).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].created_at, "i": str(page[-1].id)})


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
    if cursor:
        stmt = stmt.where(Station.created_at > datetime.fromisoformat(cursor["t"]))
    rows = list(
        (await session.execute(stmt.order_by(Station.created_at, Station.id).limit(limit + 1))).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].created_at, "i": str(page[-1].id)})


async def version_for_attempt(
    session: AsyncSession, org_id: uuid.UUID | None, version_id: uuid.UUID
) -> tuple[StationVersion, Station] | None:
    """A version an attempt may run, with the station that owns it.

    Scoped deliberately: a platform library station (`org_id IS NULL`) is
    available to everyone, and an org's own station only to that org. Without
    the second half this would be a global lookup by id, which is the shape
    that leaks across tenants elsewhere in the legacy code.
    """
    owner = (
        Station.org_id.is_(None)
        if org_id is None
        else or_(Station.org_id.is_(None), Station.org_id == org_id)
    )
    stmt = (
        select(StationVersion, Station)
        .join(Station, Station.id == StationVersion.station_id)
        .where(StationVersion.id == version_id, owner)
    )
    row = (await session.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def feedback_template_version(
    session: AsyncSession, org_id: uuid.UUID, version_id: uuid.UUID
) -> FeedbackTemplateVersion | None:
    """One of this org's feedback template versions, scoped to it."""
    stmt = select(FeedbackTemplateVersion).where(
        FeedbackTemplateVersion.org_id == org_id,
        FeedbackTemplateVersion.id == version_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()
