"""The periodic health sweep: stalled jobs, abandoned attempts, and its own failures (S-25)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction
from app.features.attempts import repository
from app.features.attempts.models import Attempt
from app.features.health import service
from app.features.identity import repository as identity_repo
from app.features.tenancy.models import AuditEntry
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


async def _attempt(session: AsyncSession, *, kind: str, status: str, age: timedelta) -> uuid.UUID:
    user = await identity_repo.create_user(
        session, email=f"w{uuid.uuid4().hex[:8]}@example.com", name="W", password_hash=None
    )
    exam = await ensure_exam(session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(session, kind=kind, user_id=user.id, exam_id=exam.id)
    await repository.set_status(session, attempt.id, status=status, at=NOW - age)
    await session.execute(
        text("UPDATE attempts SET created_at = :at WHERE id = :id"), {"at": NOW - age, "id": attempt.id}
    )
    return attempt.id


async def _state(session: AsyncSession, attempt_id: uuid.UUID) -> tuple[str, str | None]:
    row = (
        await session.execute(select(Attempt.status, Attempt.failed_reason).where(Attempt.id == attempt_id))
    ).one()
    return row.status, row.failed_reason


async def test_a_consumer_attempt_stuck_for_over_three_hours_is_failed_as_abandoned(
    db_session: AsyncSession,
) -> None:
    stuck_created = await _attempt(db_session, kind="practice", status="created", age=timedelta(hours=4))
    stuck_running = await _attempt(db_session, kind="self_practice", status="running", age=timedelta(hours=5))
    recent = await _attempt(db_session, kind="practice", status="running", age=timedelta(hours=2))
    done = await _attempt(db_session, kind="practice", status="interaction_complete", age=timedelta(hours=9))

    abandoned = await service.abandon_stale_attempts(db_session, now=NOW)

    assert sorted(abandoned) == sorted([stuck_created, stuck_running])
    assert await _state(db_session, stuck_created) == ("failed", "abandoned")
    assert await _state(db_session, stuck_running) == ("failed", "abandoned")
    assert await _state(db_session, recent) == ("running", None)
    assert await _state(db_session, done) == ("interaction_complete", None)


async def test_a_stalled_job_is_requeued_three_times_then_failed_with_the_reason_recorded(
    db_session: AsyncSession,
) -> None:
    await defer_in_transaction(
        db_session, queue="health", task="x_task", args={}, queueing_lock=f"x-{uuid.uuid4()}"
    )
    job_id = (await db_session.execute(text("SELECT max(id) FROM procrastinate_jobs"))).scalar_one()

    async def dies_while_running() -> None:
        await db_session.execute(
            text("UPDATE procrastinate_jobs SET status = 'doing', worker_id = NULL WHERE id = :id"),
            {"id": job_id},
        )

    for _ in range(3):
        await dies_while_running()
        assert job_id in (await service.reclaim_stalled_jobs(db_session))[0]
    await dies_while_running()
    assert job_id in (await service.reclaim_stalled_jobs(db_session))[1]

    entry = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "job.stalled_failed"))
    ).scalar_one()
    assert (entry.org_id, entry.actor_user_id, entry.target_id) == (None, None, str(job_id))
    assert entry.meta == {"task": "x_task", "requeues": 3}


async def test_a_failing_sweep_step_is_recorded_for_staff_and_the_next_step_still_runs(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    stuck = await _attempt(db_session, kind="practice", status="created", age=timedelta(hours=4))

    async def broken(session: AsyncSession) -> tuple[list[int], list[int]]:
        raise RuntimeError("queue unreadable")

    monkeypatch.setattr(service, "reclaim_stalled_jobs", broken)

    @asynccontextmanager
    async def opener() -> AsyncIterator[AsyncSession]:
        yield db_session

    await service.run_sweep(opener, now=NOW)

    entry = (
        await db_session.execute(select(AuditEntry).where(AuditEntry.action == "sweep.failed"))
    ).scalar_one()
    assert (entry.org_id, entry.target_id, entry.meta) == (
        None,
        "reclaim_stalled_jobs",
        {"error": "RuntimeError: queue unreadable"},
    )
    assert await _state(db_session, stuck) == ("failed", "abandoned")
