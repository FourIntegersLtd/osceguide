"""Storage for the queue of reports readers have filed against stations.

The queue has its own filters (open or resolved) and its own sort (oldest first, because the oldest
report is the one that has waited).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.stations.models import Station, StationFlag


async def find(session: AsyncSession, *, station_id: uuid.UUID, user_id: uuid.UUID) -> StationFlag | None:
    stmt = select(StationFlag).where(
        StationFlag.station_id == station_id,
        StationFlag.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add(session: AsyncSession, *, station_id: uuid.UUID, user_id: uuid.UUID) -> StationFlag:
    row = StationFlag(station_id=station_id, user_id=user_id)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def by_id(session: AsyncSession, flag_id: uuid.UUID) -> StationFlag | None:
    return await session.get(StationFlag, flag_id)


async def for_reporter(session: AsyncSession, user_id: uuid.UUID) -> list[tuple[StationFlag, str | None]]:
    """Everything this person has reported, with the station's title.

    Joined here rather than resolved client-side, so a report on a station that is not on the
    caller's current page still shows a real title instead of "Unknown Station".
    """
    stmt = (
        select(StationFlag, Station.title)
        .join(Station, Station.id == StationFlag.station_id)
        .where(StationFlag.user_id == user_id)
        .order_by(StationFlag.created_at.desc())
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]


async def list_page(
    session: AsyncSession,
    *,
    status: str | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[StationFlag], str | None]:
    """The staff queue. `status=None` is everything, which is what "show me
    what we have already answered" needs."""
    stmt: Select[Any] = select(StationFlag)
    if status is not None:
        stmt = stmt.where(StationFlag.status == status)
    return await keyset_page(
        session,
        stmt,
        sort_col=StationFlag.created_at,
        id_col=StationFlag.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def titles_by_ids(session: AsyncSession, station_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Titles for a page of flags, one query.

    `keyset_page` returns scalars, so the queue cannot carry the title out with
    the row and has to ask for the page's ids in a second read.
    """
    if not station_ids:
        return {}
    stmt = select(Station.id, Station.title).where(Station.id.in_(station_ids))
    return {row[0]: row[1] for row in (await session.execute(stmt)).all()}


async def set_resolved(
    session: AsyncSession,
    row: StationFlag,
    *,
    status: str,
    note: str | None,
    actor_id: uuid.UUID,
    resolved_at: datetime | None,
) -> StationFlag:
    row.status = status
    row.resolution_note = note
    row.resolved_by = actor_id
    row.resolved_at = resolved_at
    await session.flush()
    await session.refresh(row)
    return row
