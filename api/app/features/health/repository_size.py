"""How big the database is, live and as the daily readings kept it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.health.models import DatabaseSizeReading


@dataclass(frozen=True)
class RelationSize:
    """One table with its indexes and TOAST, and what a row of it costs."""

    name: str
    total_bytes: int
    # An estimate from the planner's statistics (`reltuples`), which autovacuum keeps; None until analysed.
    rows: int | None
    bytes_per_row: int | None


@dataclass(frozen=True)
class Reading:
    """One day's stored reading."""

    taken_on: date
    total_bytes: int
    relations: list[dict[str, Any]]
    alert_level: int


async def lock_alarm(session: AsyncSession) -> None:
    """Hold the size alarm for this transaction, so a second run waits for the first to commit."""
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("database_size_alarm", 0))))


async def limit_statement_time(session: AsyncSession, *, seconds: float) -> None:
    """Have the server cancel any statement of this transaction that runs longer than `seconds`."""
    await session.execute(
        text("select set_config('statement_timeout', :ms, true)"), {"ms": str(int(seconds * 1000))}
    )


async def restore_statement_time(session: AsyncSession) -> None:
    """Take the limit off again, so the rest of the request's transaction is not held to it."""
    await session.execute(text("reset statement_timeout"))


async def database_bytes(session: AsyncSession) -> int:
    """The whole database on disk, as the host's quota counts it."""
    return int((await session.execute(text("select pg_database_size(current_database())"))).scalar_one())


async def top_relations(session: AsyncSession, *, limit: int) -> list[RelationSize]:
    """The biggest tables in `public`, largest first, each with its indexes and TOAST."""
    rows = await session.execute(
        text(
            "select c.relname as name, pg_total_relation_size(c.oid) as total_bytes, "
            "greatest(c.reltuples, 0)::bigint as rows "
            "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relkind = 'r' "
            "order by pg_total_relation_size(c.oid) desc, c.relname limit :limit"
        ),
        {"limit": limit},
    )
    return [
        RelationSize(
            name=row.name,
            total_bytes=int(row.total_bytes),
            rows=int(row.rows) if row.rows else None,
            bytes_per_row=int(row.total_bytes) // int(row.rows) if row.rows else None,
        )
        for row in rows
    ]


def _read(row: DatabaseSizeReading) -> Reading:
    """One stored daily reading, handed on without the database row behind it."""
    return Reading(
        taken_on=row.taken_on,
        total_bytes=row.total_bytes,
        relations=list(row.relations),
        alert_level=row.alert_level,
    )


async def readings_since(session: AsyncSession, since: date) -> list[Reading]:
    """Readings from `since` on, oldest first."""
    rows = await session.execute(
        select(DatabaseSizeReading)
        .where(DatabaseSizeReading.taken_on >= since)
        .order_by(DatabaseSizeReading.taken_on)
    )
    return [_read(row) for row in rows.scalars()]


async def latest_reading(session: AsyncSession) -> Reading | None:
    """The newest stored reading, today's if there is one."""
    row = (
        await session.execute(
            select(DatabaseSizeReading).order_by(DatabaseSizeReading.taken_on.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return _read(row) if row else None


async def save_reading(
    session: AsyncSession,
    *,
    taken_on: date,
    total_bytes: int,
    relations: list[dict[str, Any]],
    alert_level: int,
) -> None:
    """Store the day's reading; a second one the same day replaces the first."""
    values = {
        "taken_on": taken_on,
        "total_bytes": total_bytes,
        "relations": relations,
        "alert_level": alert_level,
    }
    await session.execute(
        insert(DatabaseSizeReading)
        .values(**values)
        .on_conflict_do_update(
            constraint="uq_database_size_readings_taken_on",
            set_={
                **{column: value for column, value in values.items() if column != "taken_on"},
                "updated_at": text("now()"),
            },
        )
    )


async def trim_readings_before(session: AsyncSession, day: date) -> None:
    """Drop readings older than `day`: the forecast looks back two months, the history keeps over a year."""
    await session.execute(delete(DatabaseSizeReading).where(DatabaseSizeReading.taken_on < day))
