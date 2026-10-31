"""How full the database is: measured live for the console, recorded daily for the trend and the alarm."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import get_args

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings, get_settings
from app.features.health import domain, repository_size
from app.features.health.repository_size import RelationSize
from app.features.health.schemas import DatabaseSizeRead, RelationSizeRead, SizeForecastRead, SizeLevel
from app.features.tenancy import service_audit

TOP_RELATIONS = 10
# The forecast fits the last two months; the history is kept for a year and a bit, to see a season.
READING_RETENTION_DAYS = 400
MIB = domain.MIB


def _history(stored: list[repository_size.Reading], today: date, total_bytes: int) -> list[tuple[date, int]]:
    """The stored days before today, then today's figure just measured."""
    return [(reading.taken_on, reading.total_bytes) for reading in stored if reading.taken_on < today] + [
        (today, total_bytes)
    ]


def _relation_dicts(relations: list[RelationSize]) -> list[dict[str, int | str | None]]:
    """The biggest tables as plain values, the shape the audit row and the stored reading both keep."""
    return [
        {"name": relation.name, "total_bytes": relation.total_bytes, "rows": relation.rows}
        for relation in relations
    ]


def _sentence(total_bytes: int, budget_bytes: int, forecast: domain.Forecast) -> str:
    """The one line staff read in the audit log and the alert: how full the database is and when it fills."""
    percent = round(total_bytes / budget_bytes * 100)
    return (
        f"The database is at {percent}% of its {round(budget_bytes / MIB)} MB budget "
        f"({round(total_bytes / MIB)} MB). {domain.describe(forecast)}"
    )


@dataclass(frozen=True)
class Measured:
    """The database as it is now: its size, its biggest tables and where the trend is heading."""

    total_bytes: int
    budget_bytes: int
    level: int
    relations: list[RelationSize]
    forecast: domain.Forecast


async def _measure(session: AsyncSession, *, now: datetime, budget_bytes: int) -> Measured:
    """Read the size and history and fit the forecast: what the console and the daily task share."""
    total_bytes = await repository_size.database_bytes(session)
    relations = await repository_size.top_relations(session, limit=TOP_RELATIONS)
    today = now.date()
    stored = await repository_size.readings_since(session, today - timedelta(days=domain.WINDOW_DAYS))
    return Measured(
        total_bytes=total_bytes,
        budget_bytes=budget_bytes,
        level=domain.alert_level(total_bytes, budget_bytes),
        relations=relations,
        forecast=domain.forecast(_history(stored, today, total_bytes), budget_bytes),
    )


async def database_size(
    session: AsyncSession, *, now: datetime, settings: Settings | None = None
) -> DatabaseSizeRead:
    """The size right now, the biggest tables and the forecast. Needs no worker and no stored reading."""
    budget_bytes = (settings or get_settings()).database_size_budget_mb * MIB
    measured = await _measure(session, now=now, budget_bytes=budget_bytes)
    forecast = measured.forecast
    return DatabaseSizeRead(
        total_bytes=measured.total_bytes,
        budget_bytes=budget_bytes,
        percent_used=round(measured.total_bytes / budget_bytes * 100, 1),
        level=get_args(SizeLevel)[measured.level],
        top_relations=[RelationSizeRead(**relation.__dict__) for relation in measured.relations],
        forecast=SizeForecastRead(
            state=forecast.state,
            bytes_per_day=forecast.bytes_per_day,
            days_until_full=forecast.days_until_full,
            readings_used=forecast.readings_used,
            note=domain.describe(forecast),
        ),
    )


async def record_database_size(session: AsyncSession, *, now: datetime) -> str | None:
    """Store today's reading and write the audit row for each threshold it has newly crossed.

    Returns the sentence to page a person with when the 80% threshold was newly crossed, else None.
    The caller sends it once this transaction has committed: a page sent from inside would go out
    again when a failed commit is retried, since the retry finds no stored crossing.

    A reading is kept once a day, so a rerun replaces it. The alarm compares against the level the
    previous reading (today's, on a rerun) was stored at, so each crossing raises it once however
    often this runs; falling back below a threshold and crossing it again is a second crossing. The
    advisory lock makes the compare and the write one step, so two runs at once (the daily task and
    a retry) cannot both see the old level.
    """
    await repository_size.lock_alarm(session)
    budget_bytes = get_settings().database_size_budget_mb * MIB
    measured = await _measure(session, now=now, budget_bytes=budget_bytes)
    previous = await repository_size.latest_reading(session)
    already_raised = previous.alert_level if previous else 0

    summary = _sentence(measured.total_bytes, budget_bytes, measured.forecast)
    meta = {
        "total_bytes": measured.total_bytes,
        "budget_bytes": budget_bytes,
        "forecast": measured.forecast.state,
        "days_until_full": measured.forecast.days_until_full,
        "top_relations": _relation_dicts(measured.relations[:3]),
    }
    for threshold, action in ((1, "database.size_warning"), (2, "database.size_critical")):
        if already_raised < threshold <= measured.level:
            await service_audit.record_system(
                session,
                action=action,
                target_type="database",
                target_id="size",
                summary=summary,
                meta=meta,
                at=now,
            )

    today = now.date()
    await repository_size.save_reading(
        session,
        taken_on=today,
        total_bytes=measured.total_bytes,
        relations=_relation_dicts(measured.relations),
        alert_level=measured.level,
    )
    await repository_size.trim_readings_before(session, today - timedelta(days=READING_RETENTION_DAYS))
    return summary if already_raised < 2 <= measured.level else None
