"""Storage for practice sets. Owned by a user, so scoped by owner rather than org."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.station_sets.models import StationSet, StationSetEntry


async def create_set(
    session: AsyncSession, owner_user_id: uuid.UUID, *, exam_id: uuid.UUID, name: str
) -> StationSet:
    row = StationSet(owner_user_id=owner_user_id, exam_id=exam_id, name=name)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def add_entries(
    session: AsyncSession, set_id: uuid.UUID, *, station_version_ids: list[uuid.UUID]
) -> list[StationSetEntry]:
    rows = [
        StationSetEntry(set_id=set_id, position=i, station_version_id=station_version_id)
        for i, station_version_id in enumerate(station_version_ids)
    ]
    session.add_all(rows)
    await session.flush()
    for row in rows:
        await session.refresh(row)
    return rows


async def set_by_id(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> StationSet | None:
    stmt = select(StationSet).where(StationSet.owner_user_id == owner_user_id, StationSet.id == set_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def entries_for(session: AsyncSession, set_id: uuid.UUID) -> list[StationSetEntry]:
    stmt = select(StationSetEntry).where(StationSetEntry.set_id == set_id).order_by(StationSetEntry.position)
    return list((await session.execute(stmt)).scalars())


async def entry_by_id(
    session: AsyncSession, set_id: uuid.UUID, entry_id: uuid.UUID
) -> StationSetEntry | None:
    stmt = select(StationSetEntry).where(StationSetEntry.set_id == set_id, StationSetEntry.id == entry_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def record_attempt(
    session: AsyncSession, entry_id: uuid.UUID, *, at: datetime, debrief: bool = False
) -> None:
    """Increment in the database rather than read-modify-write.

    b2c mutates an array on the user document without a transaction, so two
    sessions finishing at once lose one of the counts.
    """
    column = StationSetEntry.debrief_attempts if debrief else StationSetEntry.attempts
    await session.execute(
        update(StationSetEntry)
        .where(StationSetEntry.id == entry_id)
        .values({column: column + 1, StationSetEntry.last_attempt_at: at})
    )


async def mark_complete(session: AsyncSession, set_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(update(StationSet).where(StationSet.id == set_id).values(completed_at=at))


async def set_locked(session: AsyncSession, owner_user_id: uuid.UUID, *, locked: bool) -> None:
    await session.execute(
        update(StationSet).where(StationSet.owner_user_id == owner_user_id).values(locked=locked)
    )


async def list_for_owner(
    session: AsyncSession, owner_user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[StationSet], str | None]:
    stmt = select(StationSet).where(StationSet.owner_user_id == owner_user_id)
    if cursor:
        stmt = stmt.where(StationSet.created_at < datetime.fromisoformat(cursor["t"]))
    rows = list(
        (
            await session.execute(
                stmt.order_by(StationSet.created_at.desc(), StationSet.id.desc()).limit(limit + 1)
            )
        ).scalars()
    )
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor({"t": page[-1].created_at, "i": str(page[-1].id)})
