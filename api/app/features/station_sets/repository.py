"""Storage for practice sets. Owned by a user, so scoped by owner rather than org."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.core.search import contains_text
from app.features.station_sets.models import StationSet, StationSetEntry


async def create_set(
    session: AsyncSession, owner_user_id: uuid.UUID, *, exam_id: uuid.UUID, name: str
) -> StationSet:
    """Start a new, empty practice set for this person. `add_entries` fills it in."""
    station_set = StationSet(owner_user_id=owner_user_id, exam_id=exam_id, name=name)
    session.add(station_set)
    await session.flush()
    await session.refresh(station_set)
    return station_set


async def add_entries(
    session: AsyncSession, set_id: uuid.UUID, *, station_version_ids: list[uuid.UUID]
) -> list[StationSetEntry]:
    """Add stations to a set in the given order, starting at position 0."""
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
    """One set, only if it belongs to this owner. `None` for someone else's set or a bad id."""
    stmt = select(StationSet).where(StationSet.owner_user_id == owner_user_id, StationSet.id == set_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def rename_set(session: AsyncSession, station_set: StationSet, *, name: str) -> None:
    """Write the name. The owner was checked by whoever loaded the record."""
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
    """A set's stations in the order they were added."""
    stmt = select(StationSetEntry).where(StationSetEntry.set_id == set_id).order_by(StationSetEntry.position)
    return list((await session.execute(stmt)).scalars())


async def entry_by_id(
    session: AsyncSession, set_id: uuid.UUID, entry_id: uuid.UUID
) -> StationSetEntry | None:
    """One station inside a set, only if it belongs to that set."""
    stmt = select(StationSetEntry).where(StationSetEntry.set_id == set_id, StationSetEntry.id == entry_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def delete_entries(session: AsyncSession, set_id: uuid.UUID, entry_ids: Collection[uuid.UUID]) -> None:
    """Remove specific entries from one set, by id.

    Only ever called once the caller has confirmed none of them has an
    attempt against it: an entry with attempts `RESTRICT`s, so this would
    otherwise fail on the foreign key rather than explain itself.
    """
    if not entry_ids:
        return
    await session.execute(
        delete(StationSetEntry).where(
            StationSetEntry.set_id == set_id, StationSetEntry.id.in_(list(entry_ids))
        )
    )


async def park_entries(session: AsyncSession, entry_ids: Collection[uuid.UUID]) -> None:
    """Move these entries to positions nothing else in the set will ever hold (negative ones).

    Called before inserting replacement entries at positions `0..n`, so a kept
    entry that already happens to sit at one of those low numbers is out of the
    way rather than colliding with the unique `(set_id, position)` the moment
    the new row is written.
    """
    for offset, entry_id in enumerate(entry_ids):
        await session.execute(
            update(StationSetEntry).where(StationSetEntry.id == entry_id).values(position=-(offset + 1))
        )


async def reposition_entries(session: AsyncSession, ordered_entry_ids: list[uuid.UUID]) -> None:
    """Renumber a set's entries to `0..n-1` in exactly this order.

    Two passes, not one: entries scattered across both a leftover negative
    range (parked kept entries) and a small non-negative range (entries just
    inserted) would collide with the unique `(set_id, position)` if written
    straight to their final numbers, because some entry already sits at almost
    every number below `n`. Landing everything on a range more negative than
    any of those first guarantees nothing already occupies a target position
    when the second pass writes it.
    """
    total = len(ordered_entry_ids)
    for offset, entry_id in enumerate(ordered_entry_ids):
        await session.execute(
            update(StationSetEntry)
            .where(StationSetEntry.id == entry_id)
            .values(position=-(total + offset + 1))
        )
    for position, entry_id in enumerate(ordered_entry_ids):
        await session.execute(
            update(StationSetEntry).where(StationSetEntry.id == entry_id).values(position=position)
        )


async def try_record_started_attempt(
    session: AsyncSession, entry_id: uuid.UUID, *, at: datetime, limit: int, debrief: bool = False
) -> uuid.UUID | None:
    """Count one *started* attempt against an entry's limit, or refuse if it is already spent.

    A single conditional `UPDATE ... WHERE <column> < limit`, not a `SELECT` followed by an
    `UPDATE`: two callers both crediting the last allowed attempt for the same entry at once must
    not both succeed, and there is no lock to hold in between two separate statements. Postgres
    serialises concurrent updates to the same row itself, so the second caller's `WHERE` re-reads
    the first caller's write rather than a stale count.

    Zero means unlimited (an org-granted set), so the guard is skipped and the write always applies.
    Returns the entry's `set_id` if the count was applied, so the caller can re-check whether the
    whole set just became complete without a second round trip; `None` means the limit was already
    used up and nothing was written.
    """
    column = StationSetEntry.debrief_attempts if debrief else StationSetEntry.attempts
    statement = (
        update(StationSetEntry)
        .where(StationSetEntry.id == entry_id)
        .values({column: column + 1, StationSetEntry.last_attempt_at: at})
        .returning(StationSetEntry.set_id)
    )
    if limit:
        statement = statement.where(column < limit)
    return (await session.execute(statement)).scalar_one_or_none()


async def mark_complete(session: AsyncSession, set_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(update(StationSet).where(StationSet.id == set_id).values(completed_at=at))


async def set_locked(session: AsyncSession, owner_user_id: uuid.UUID, *, locked: bool) -> None:
    """Lock or unlock every set this person owns, as their access lapses or renews."""
    await session.execute(
        update(StationSet).where(StationSet.owner_user_id == owner_user_id).values(locked=locked)
    )


async def list_for_owner(
    session: AsyncSession, owner_user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[StationSet], str | None]:
    """This person's practice sets, newest first."""
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


async def sat_version_ids(
    session: AsyncSession, owner_user_id: uuid.UUID, exam_id: uuid.UUID
) -> set[uuid.UUID]:
    """The station versions this person has sat in any of their sets for this exam."""
    stmt = (
        select(StationSetEntry.station_version_id)
        .join(StationSet, StationSet.id == StationSetEntry.set_id)
        .where(
            StationSet.owner_user_id == owner_user_id,
            StationSet.exam_id == exam_id,
            StationSetEntry.attempts > 0,
        )
    )
    return set((await session.execute(stmt)).scalars())


def _owned_entry_ids(owner_user_id: uuid.UUID, version_ids: Collection[uuid.UUID]) -> Any:
    """A subquery of this owner's set-entry ids that point at any of these station versions.

    Shared by `reset_counters` and `remove_entries`, which both need to touch every
    matching entry across every set this person owns without loading the rows first.
    """
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


async def set_counts_by_station_version(
    session: AsyncSession, station_version_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many practice sets, anyone's, include each station version."""
    if not station_version_ids:
        return {}
    stmt = (
        select(StationSetEntry.station_version_id, func.count(StationSetEntry.set_id.distinct()))
        .where(StationSetEntry.station_version_id.in_(list(station_version_ids)))
        .group_by(StationSetEntry.station_version_id)
    )
    return {version_id: int(count) for version_id, count in (await session.execute(stmt)).all()}


async def set_entry_flag(
    session: AsyncSession, set_id: uuid.UUID, entry_id: uuid.UUID, *, flagged_at: datetime | None
) -> None:
    """Flag one entry of a set (a timestamp) or clear its flag (`None`)."""
    await session.execute(
        update(StationSetEntry)
        .where(StationSetEntry.set_id == set_id, StationSetEntry.id == entry_id)
        .values(flagged_at=flagged_at)
    )


async def flagged_entries_page(
    session: AsyncSession,
    owner_user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    search: str | None = None,
    matching_version_ids: Sequence[uuid.UUID] | None = None,
) -> tuple[list[tuple[StationSetEntry, StationSet]], str | None]:
    """One page of the flagged entries across this person's sets, most recently flagged first.

    `search` matches the set's name, or a station version in `matching_version_ids` (the
    caller resolves those from station titles through the stations slice).
    """
    stmt = (
        select(StationSetEntry)
        .join(StationSet, StationSet.id == StationSetEntry.set_id)
        .where(StationSet.owner_user_id == owner_user_id, StationSetEntry.flagged_at.is_not(None))
    )
    if search:
        stmt = stmt.where(
            or_(
                contains_text(StationSet.name, search),
                StationSetEntry.station_version_id.in_(matching_version_ids or []),
            )
        )
    entries, next_cursor = await keyset_page(
        session,
        stmt,
        sort_col=StationSetEntry.flagged_at,
        id_col=StationSetEntry.id,
        limit=limit,
        cursor=cursor,
    )
    set_ids = {entry.set_id for entry in entries}
    sets_by_id = {
        station_set.id: station_set
        for station_set in (
            await session.execute(select(StationSet).where(StationSet.id.in_(set_ids)))
        ).scalars()
    }
    return [(entry, sets_by_id[entry.set_id]) for entry in entries], next_cursor
