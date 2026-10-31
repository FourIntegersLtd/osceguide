"""Two size readings that cross a threshold together write one audit row, not two.

Needs committed data and separate connections: the per-test rollback cannot show one transaction
waiting on another. The first run is held uncommitted until the second is blocked, whatever it is
blocked on, so nothing here depends on the order of calls inside the code under test.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session_factory, import_all_models
from app.core.settings import get_settings
from app.features.health import repository_size, service_size
from app.features.health.models import DatabaseSizeReading
from app.features.tenancy.models import AuditEntry
from tests.support.committed_worlds import append_only_triggers_off

pytestmark = pytest.mark.db

import_all_models()

MB = 1024 * 1024
NOW = datetime(2026, 10, 31, 4, 30, tzinfo=UTC)


async def clean() -> None:
    async with get_session_factory()() as session, session.begin():
        async with append_only_triggers_off(session, ["audit_log"]):
            await session.execute(delete(AuditEntry).where(AuditEntry.action.like("database.size%")))
        await session.execute(delete(DatabaseSizeReading))


async def someone_is_waiting() -> bool:
    async with get_session_factory()() as session:
        return bool(await session.scalar(text("SELECT count(*) FROM pg_locks WHERE NOT granted")))


async def run_and_commit(session: AsyncSession) -> None:
    async with session.begin():
        await service_size.record_database_size(session, now=NOW)


async def test_two_runs_at_once_write_one_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    async def total(_session: AsyncSession) -> int:
        return 305 * MB

    monkeypatch.setattr(repository_size, "database_bytes", total)
    monkeypatch.setattr(get_settings(), "database_size_budget_mb", 500)
    await clean()
    try:
        first = get_session_factory()()
        await first.begin()
        try:
            await service_size.record_database_size(first, now=NOW)
            second = get_session_factory()()
            try:
                racing = asyncio.create_task(run_and_commit(second))
                for _ in range(200):
                    if await someone_is_waiting():
                        break
                    await asyncio.sleep(0.05)
                else:
                    racing.cancel()
                    raise AssertionError(f"the second run never waited on the first: {racing}")
                await first.commit()
                await asyncio.wait_for(racing, timeout=10)
            finally:
                await second.close()
        finally:
            await first.close()

        async with get_session_factory()() as session:
            warnings = await session.scalar(
                select(func.count())
                .select_from(AuditEntry)
                .where(AuditEntry.action == "database.size_warning")
            )
        assert warnings == 1
    finally:
        await clean()
