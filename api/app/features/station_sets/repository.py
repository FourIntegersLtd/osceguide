"""Storage for practice sets. Owned by a user, so scoped by owner rather than org."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.station_sets.models import StationSet, StationSetEntry


async def create_set(
    session: AsyncSession, owner_user_id: uuid.UUID, *, exam_id: uuid.UUID, name: str
) -> StationSet:
    station_set = StationSet(owner_user_id=owner_user_id, exam_id=exam_id, name=name)
    session.add(station_set)
    await session.flush()
    await session.refresh(station_set)
    return station_set


async def add_entries(
    session: AsyncSession, set_id: uuid.UUID, *, station_version_ids: list[uuid.UUID]
) -> list[StationSetEntry]:
    entries = [
        StationSetEntry(set_id=set_id, position=position, station_version_id=station_version_id)
        for position, station_version_id in enumerate(station_version_ids)
    ]
    session.add_all(entries)
    await session.flush()
    for entry in entries:
        await session.refresh(entry)
    return entries


async def set_by_id(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> StationSet | None:
    stmt = select(StationSet).where(StationSet.owner_user_id == owner_user_id, StationSet.id == set_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def rename_set(session: AsyncSession, station_set: StationSet, *, name: str) -> None:
    """Write the name. The owner was checked by whoever loaded the row."""
    station_set.name = name
    await session.flush()


async def delete_set(session: AsyncSession, owner_user_id: uuid.UUID, set_id: uuid.UUID) -> None:
    """Throw a set away, its entries with it.

    The entries go on the foreign key's `ON DELETE CASCADE`. Attempts are the ones that do not
    cascade — they `RESTRICT` — so whoever calls this has already asked whether the set holds any.
    """
    await session.execute(
        delete(StationSet).where(StationSet.owner_user_id == owner_user_id, StationSet.id == set_id)
    )


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
    return await keyset_page(
        session, stmt, sort_col=StationSet.created_at, id_col=StationSet.id, limit=limit, cursor=cursor
    )


async def entries_for_owner_by_versions(
    session: AsyncSession, owner_user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> list[StationSetEntry]:
    """Every entry across this person's sets that points at one of these versions."""
    if not version_ids:
        return []
    stmt = (
        select(StationSetEntry)
        .join(StationSet, StationSet.id == StationSetEntry.set_id)
        .where(
            StationSet.owner_user_id == owner_user_id,
            StationSetEntry.station_version_id.in_(list(version_ids)),
        )
    )
    return list((await session.execute(stmt)).scalars())


def _owned_entry_ids(owner_user_id: uuid.UUID, version_ids: Collection[uuid.UUID]) -> Any:
    return (
        select(StationSetEntry.id)
        .join(StationSet, StationSet.id == StationSetEntry.set_id)
        .where(
            StationSet.owner_user_id == owner_user_id,
            StationSetEntry.station_version_id.in_(list(version_ids)),
        )
        .scalar_subquery()
    )


async def reset_counters(
    session: AsyncSession, owner_user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> int:
    """Set the attempt and debrief counters back to zero on every matching
    entry — what the old console's "reset attempts" did to `station_progress`."""
    if not version_ids:
        return 0
    update_outcome = await session.execute(
        update(StationSetEntry)
        .where(StationSetEntry.id.in_(_owned_entry_ids(owner_user_id, version_ids)))
        .values(attempts=0, debrief_attempts=0, last_attempt_at=None)
    )
    return int(getattr(update_outcome, "rowcount", 0) or 0)


async def remove_entries(
    session: AsyncSession, owner_user_id: uuid.UUID, version_ids: Collection[uuid.UUID]
) -> int:
    """Take the station out of every one of this person's sets. The attempts
    that pointed at the entries must already be gone: they `RESTRICT`."""
    if not version_ids:
        return 0
    delete_outcome = await session.execute(
        delete(StationSetEntry).where(StationSetEntry.id.in_(_owned_entry_ids(owner_user_id, version_ids)))
    )
    return int(getattr(delete_outcome, "rowcount", 0) or 0)
