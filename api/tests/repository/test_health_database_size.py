"""The daily database-size reading: what it records, when it alarms, and what happens when it fails.

The free plan flips the database read-only at 500 MB. A 60% crossing writes an audit row, an 80% crossing
also reaches Sentry, and each crossing does so once however often the task runs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings, get_settings
from app.features.health import repository_size, service, service_size
from app.features.tenancy.models import AuditEntry

pytestmark = pytest.mark.db

MB = 1024 * 1024
NOW = datetime(2026, 10, 31, 4, 30, tzinfo=UTC)


def opener_for(session: AsyncSession) -> Any:
    @asynccontextmanager
    async def opener() -> AsyncIterator[AsyncSession]:
        yield session

    return opener


def database_of(megabytes: float, monkeypatch: pytest.MonkeyPatch, *, budget_mb: int = 500) -> None:
    """Make the database measure `megabytes`, against a budget of `budget_mb`."""

    async def total(_session: AsyncSession) -> int:
        return int(megabytes * MB)

    monkeypatch.setattr(repository_size, "database_bytes", total)
    monkeypatch.setattr(get_settings(), "database_size_budget_mb", budget_mb)


async def audit_actions(session: AsyncSession, prefix: str = "database.size") -> list[str]:
    rows = await session.execute(
        select(AuditEntry.action)
        .where(AuditEntry.action.like(f"{prefix}%"))
        .order_by(AuditEntry.at, AuditEntry.id)
    )
    return list(rows.scalars())


class CapturingTransport(Transport):
    """Sentry's wire, replaced: keeps each envelope's event so a test can read what would have been sent."""

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options)
        self.events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Any) -> None:
        event = envelope.get_event()
        if event is not None:
            self.events.append(event)


@pytest.fixture
def sentry() -> Iterator[CapturingTransport]:
    transport = CapturingTransport()
    sentry_sdk.init(dsn="https://key@example.test/1", transport=transport, default_integrations=False)
    yield transport
    sentry_sdk.get_client().close()
    sentry_sdk.init()


async def test_a_reading_is_stored_once_a_day_and_rerunning_it_changes_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_of(120, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW)
    await service_size.record_database_size(db_session, now=NOW + timedelta(hours=3))

    readings = await repository_size.readings_since(db_session, NOW.date() - timedelta(days=1))
    assert [(r.taken_on, r.total_bytes) for r in readings] == [(NOW.date(), 120 * MB)]
    assert readings[0].relations, "the biggest relations are kept so a rise can be traced to a table"


async def test_the_reading_names_the_biggest_relations_with_what_a_row_costs(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(text("ANALYZE audit_log"))
    top = await repository_size.top_relations(db_session, limit=10)

    assert 1 <= len(top) <= 10
    assert [r.total_bytes for r in top] == sorted((r.total_bytes for r in top), reverse=True)
    assert all(r.bytes_per_row is None or r.bytes_per_row > 0 for r in top)
    assert all(not r.name.startswith("pg_") for r in top)


async def test_below_sixty_percent_nothing_is_raised(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, sentry: CapturingTransport
) -> None:
    database_of(299, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW)
    assert await audit_actions(db_session) == []
    assert sentry.events == []


async def test_crossing_sixty_percent_writes_one_audit_row_however_often_it_runs(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, sentry: CapturingTransport
) -> None:
    database_of(305, monkeypatch)
    for hours in (0, 1, 2):
        await service_size.record_database_size(db_session, now=NOW + timedelta(hours=hours))
    # And the next days, still above it: still the same single crossing.
    for days in (1, 2):
        await service_size.record_database_size(db_session, now=NOW + timedelta(days=days))

    assert await audit_actions(db_session) == ["database.size_warning"]
    assert sentry.events == [], "60% is for the staff screen; only 80% pages a person"


async def test_the_audit_row_says_how_full_it_is_and_which_tables_are_the_weight(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_of(305, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW)

    row = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "database.size_warning"))
    ).scalar_one()
    assert row.org_id is None and row.actor_user_id is None
    assert row.summary is not None and row.summary.startswith(
        "The database is at 61% of its 500 MB budget (305 MB)"
    )
    assert row.meta is not None
    assert row.meta["total_bytes"] == 305 * MB and row.meta["budget_bytes"] == 500 * MB
    assert row.meta["top_relations"]


async def test_crossing_eighty_percent_also_reaches_sentry_once(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, sentry: CapturingTransport
) -> None:
    database_of(305, monkeypatch)
    await service.run_size_check(opener_for(db_session), now=NOW)
    database_of(410, monkeypatch)
    await service.run_size_check(opener_for(db_session), now=NOW + timedelta(days=1))
    await service.run_size_check(opener_for(db_session), now=NOW + timedelta(days=1, hours=2))
    await service.run_size_check(opener_for(db_session), now=NOW + timedelta(days=2))

    assert sorted(await audit_actions(db_session)) == ["database.size_critical", "database.size_warning"]
    assert len(sentry.events) == 1
    assert sentry.events[0]["level"] == "error"
    assert sentry.events[0]["message"].startswith("The database is at 82% of its 500 MB budget (410 MB)")


async def test_a_jump_past_both_thresholds_records_both_crossings(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, sentry: CapturingTransport
) -> None:
    database_of(546, monkeypatch)
    await service.run_size_check(opener_for(db_session), now=NOW)
    assert sorted(await audit_actions(db_session)) == ["database.size_critical", "database.size_warning"]
    assert len(sentry.events) == 1


async def test_falling_back_and_crossing_again_is_a_second_crossing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_of(310, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW)
    database_of(190, monkeypatch)  # a compaction
    await service_size.record_database_size(db_session, now=NOW + timedelta(days=1))
    assert await audit_actions(db_session) == ["database.size_warning"]
    database_of(320, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW + timedelta(days=2))
    assert await audit_actions(db_session) == ["database.size_warning", "database.size_warning"]


async def test_the_alarm_says_how_long_is_left_once_there_is_history(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    for day in range(20):
        await repository_size.save_reading(
            db_session,
            taken_on=NOW.date() - timedelta(days=20 - day),
            total_bytes=(260 + 2 * day) * MB,
            relations=[],
            alert_level=0,
        )
    database_of(300, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW)

    row = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "database.size_warning"))
    ).scalar_one()
    assert row.summary is not None
    assert row.summary.endswith("At the current rate of 2 MB a day it reaches the budget in about 14 weeks.")


async def test_readings_older_than_the_retention_are_trimmed(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = NOW.date() - timedelta(days=service_size.READING_RETENTION_DAYS + 1)
    kept = NOW.date() - timedelta(days=service_size.READING_RETENTION_DAYS - 1)
    for day in (old, kept):
        await repository_size.save_reading(
            db_session, taken_on=day, total_bytes=100 * MB, relations=[], alert_level=0
        )
    database_of(120, monkeypatch)
    await service_size.record_database_size(db_session, now=NOW)

    days = [r.taken_on for r in await repository_size.readings_since(db_session, date(2020, 1, 1))]
    assert days == [kept, NOW.date()]


async def test_a_hung_size_read_degrades_to_null_and_leaves_the_session_usable(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The size is last on the console's health page and shares its session with the checks before it.

    Abandoning a query mid-flight on that session breaks it for every later statement, so the staff
    health endpoint would go down with the one reading that is slow. The reading has to give up
    without taking the session with it.
    """

    async def hang(session: AsyncSession) -> int:
        await session.execute(text("select pg_sleep(30)"))
        return 0

    monkeypatch.setattr(repository_size, "database_bytes", hang)
    monkeypatch.setattr(service, "CHECK_TIMEOUT_SECONDS", 0.3)

    report = await service.platform_health(db_session, None)

    assert report.database_size is None
    assert report.checks["database"] == "ok"
    assert report.jobs_by_status is not None
    again = await service.platform_health(db_session, None)
    assert again.checks["database"] == "ok" and again.database_size is None
    assert (await db_session.execute(text("select 1"))).scalar_one() == 1


class FailsToCommitOnce:
    """An opener whose first transaction does its work and then fails to commit: its writes are undone."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.opened = 0

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[AsyncSession]:
        self.opened += 1
        if self.opened > 1:
            yield self.session
            return
        async with self.session.begin_nested():
            yield self.session
            raise RuntimeError("commit failed")


async def test_a_commit_that_fails_does_not_page_and_the_retry_pages_once(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, sentry: CapturingTransport
) -> None:
    """The page goes out after the commit: a reading that never became durable must not have paged,
    or the retry (which finds no stored crossing) pages the same crossing a second time."""
    database_of(410, monkeypatch)
    opener = FailsToCommitOnce(db_session)

    await service.run_size_check(opener, now=NOW)
    assert sentry.events == []
    await service.run_size_check(opener, now=NOW + timedelta(hours=1))

    assert len(sentry.events) == 1
    assert sorted(await audit_actions(db_session)) == ["database.size_critical", "database.size_warning"]


async def test_a_failing_reading_is_written_to_the_audit_log_not_lost(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def explode(_session: AsyncSession) -> int:
        raise RuntimeError("catalog unreadable")

    monkeypatch.setattr(repository_size, "database_bytes", explode)
    await service.run_size_check(opener_for(db_session), now=NOW)

    row = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "sweep.failed"))
    ).scalar_one()
    assert row.target_id == "record_database_size"
    assert row.summary is not None and "catalog unreadable" in row.summary


async def test_pruning_asks_procrastinate_to_delete_succeeded_jobs_past_the_retention(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[int] = []

    async def library_delete(*, nb_hours: int, **_: Any) -> None:
        asked.append(nb_hours)

    monkeypatch.setattr(get_settings(), "job_history_retention_days", 14)
    await service.run_job_pruning(opener_for(db_session), delete_old_jobs=library_delete, now=NOW)
    assert asked == [14 * 24]


async def test_pruning_records_how_many_jobs_it_removed(db_session: AsyncSession) -> None:
    async def delete_old() -> None:
        await db_session.execute(text("DELETE FROM procrastinate_jobs WHERE task_name = 'old'"))

    for _ in range(3):
        await db_session.execute(
            text(
                "INSERT INTO procrastinate_jobs (queue_name, task_name, status, args) "
                "VALUES ('q', 'old', 'todo', '{}')"
            )
        )
    await db_session.execute(
        text("UPDATE procrastinate_jobs SET status = 'succeeded' WHERE task_name = 'old'")
    )
    await db_session.execute(
        text(
            "INSERT INTO procrastinate_events (job_id, type, at) "
            "SELECT id, 'succeeded', :finished FROM procrastinate_jobs WHERE task_name = 'old'"
        ),
        {"finished": NOW - timedelta(days=30)},
    )
    # A job still waiting is not the library's to delete, so it is not counted.
    await db_session.execute(
        text(
            "INSERT INTO procrastinate_jobs (queue_name, task_name, status, args) "
            "VALUES ('q', 'new', 'todo', '{}')"
        )
    )

    async def library_delete(*, nb_hours: int, **_: Any) -> None:
        await delete_old()

    await service.run_job_pruning(opener_for(db_session), delete_old_jobs=library_delete, now=NOW)

    row = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "jobs.pruned"))
    ).scalar_one()
    assert row.meta is not None and row.meta["removed"] == 3
    assert row.summary == "Removed 3 succeeded jobs and their events older than 14 days."


async def test_a_failing_prune_is_written_to_the_audit_log_not_lost(db_session: AsyncSession) -> None:
    async def library_delete(*, nb_hours: int, **_: Any) -> None:
        raise RuntimeError("connection reset")

    await service.run_job_pruning(opener_for(db_session), delete_old_jobs=library_delete, now=NOW)

    row = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "sweep.failed"))
    ).scalar_one()
    assert row.target_id == "prune_job_history"
    assert row.summary is not None and "connection reset" in row.summary


async def test_deleting_a_job_takes_its_events_with_it(db_session: AsyncSession) -> None:
    """The reason `procrastinate_events` needs no pruning of its own: the library's delete cascades."""
    job_id = (
        await db_session.execute(
            text(
                "INSERT INTO procrastinate_jobs (queue_name, task_name, status, args) "
                "VALUES ('q', 'cascade_probe', 'todo', '{}') RETURNING id"
            )
        )
    ).scalar_one()
    before = (
        await db_session.execute(
            text("SELECT count(*) FROM procrastinate_events WHERE job_id = :j"), {"j": job_id}
        )
    ).scalar_one()
    assert before >= 1, "an insert logs a `deferred` event by trigger"

    await db_session.execute(text("DELETE FROM procrastinate_jobs WHERE id = :j"), {"j": job_id})
    after = (
        await db_session.execute(
            text("SELECT count(*) FROM procrastinate_events WHERE job_id = :j"), {"j": job_id}
        )
    ).scalar_one()
    assert after == 0


def test_the_budget_and_retention_default_to_the_free_plan_and_two_weeks() -> None:
    fresh = Settings()
    assert fresh.database_size_budget_mb == 500
    assert fresh.job_history_retention_days == 14
