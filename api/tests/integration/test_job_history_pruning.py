"""The daily job-history prune against procrastinate's real `delete_old_jobs`, not a stand-in.

The unit-level tests hand the service a fake delete, so nothing there would notice the library
changing what that call takes, returns or deletes. This one runs the library's own task on the
queue's real tables: committed rows, since the library works on its own connection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session_factory, import_all_models
from app.core.jobs import get_jobs_app
from app.core.settings import get_settings
from app.features.health import service
from app.features.tenancy.models import AuditEntry
from tests.support.committed_worlds import append_only_triggers_off

pytestmark = pytest.mark.db

import_all_models()

# procrastinate prunes against Postgres now(), so the fixture ages are taken from the real clock.
# A pinned date silently drifts: the "1 day old" job turned 14 days old and was pruned.
KINDS = ("prune_probe_old_ok", "prune_probe_old_failed", "prune_probe_new_ok")


@asynccontextmanager
async def committed() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session, session.begin():
        yield session


async def add_job(task: str, status: str, *, age_days: int) -> None:
    async with committed() as session:
        await session.execute(
            text(
                "INSERT INTO procrastinate_jobs (queue_name, task_name, status, args) "
                "VALUES ('q', :task, 'todo', '{}')"
            ),
            {"task": task},
        )
        await session.execute(
            text("UPDATE procrastinate_jobs SET status = :s WHERE task_name = :task"),
            {"s": status, "task": task},
        )
        await session.execute(
            text(
                "INSERT INTO procrastinate_events (job_id, type, at) "
                "SELECT id, CAST(:s AS procrastinate_job_event_type), now() "
                "FROM procrastinate_jobs WHERE task_name = :task"
            ),
            {"s": status, "task": task},
        )
        await session.execute(
            text(
                "UPDATE procrastinate_events SET at = :at "
                "WHERE job_id IN (SELECT id FROM procrastinate_jobs WHERE task_name = :task)"
            ),
            {"at": datetime.now(UTC) - timedelta(days=age_days), "task": task},
        )


async def probes_left() -> list[str]:
    async with committed() as session:
        rows = await session.execute(
            text("SELECT task_name FROM procrastinate_jobs WHERE task_name = ANY(:k) ORDER BY task_name"),
            {"k": list(KINDS)},
        )
        return list(rows.scalars())


@asynccontextmanager
async def probe_jobs() -> AsyncIterator[None]:
    try:
        yield
    finally:
        async with committed() as session:
            await session.execute(
                text("DELETE FROM procrastinate_jobs WHERE task_name = ANY(:k)"), {"k": list(KINDS)}
            )
            async with append_only_triggers_off(session, ["audit_log"]):
                await session.execute(delete(AuditEntry).where(AuditEntry.action == "jobs.pruned"))


async def test_the_real_delete_old_jobs_removes_old_succeeded_jobs_and_keeps_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "job_history_retention_days", 14)
    async with probe_jobs():
        await add_job("prune_probe_old_ok", "succeeded", age_days=30)
        await add_job("prune_probe_old_failed", "failed", age_days=30)
        await add_job("prune_probe_new_ok", "succeeded", age_days=1)

        app = get_jobs_app()
        async with app.open_async():
            await service.run_job_pruning(
                committed,
                delete_old_jobs=app.job_manager.delete_old_jobs,
                now=datetime.now(UTC),
            )

        assert await probes_left() == ["prune_probe_new_ok", "prune_probe_old_failed"]
        async with committed() as session:
            row = (
                await session.execute(select(AuditEntry).where(AuditEntry.action == "jobs.pruned"))
            ).scalar_one()
        assert row.meta is not None and row.meta["removed"] == 1
