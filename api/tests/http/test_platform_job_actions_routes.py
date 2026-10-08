"""What the console may do to a job: retry a failed one, cancel a stalled or waiting one."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_job(db_session: AsyncSession, *, task: str, status: str, **args: str) -> int:
    await defer_in_transaction(db_session, queue="default", task=task, queueing_lock=None, args=args)
    found = await db_session.execute(text("SELECT max(id) FROM procrastinate_jobs"))
    job_id = int(found.scalar_one())
    await db_session.execute(
        text("UPDATE procrastinate_jobs SET status = :status WHERE id = :id"),
        {"status": status, "id": job_id},
    )
    return job_id


async def status_of(db_session: AsyncSession, job_id: int) -> str:
    found = await db_session.execute(
        text("SELECT status FROM procrastinate_jobs WHERE id = :id"), {"id": job_id}
    )
    return str(found.scalar_one())


async def test_a_failed_job_that_is_not_marking_is_queued_again(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    job_id = await a_job(db_session, task="produce_media", status="failed", media_id=str(uuid.uuid4()))

    retried = await client.post(f"/api/v1/platform/jobs/{job_id}/retry", headers=bearer(root))

    assert retried.status_code == 204, retried.text
    assert await status_of(db_session, job_id) == "todo"
    again = await client.post(f"/api/v1/platform/jobs/{job_id}/retry", headers=bearer(root))
    assert again.status_code == 409
    assert again.json()["code"] == "job_not_retryable"


async def test_a_failed_marking_is_retried_through_its_attempt_not_here(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    job_id = await a_job(db_session, task="score_attempt", status="failed", attempt_id=str(uuid.uuid4()))

    refused = await client.post(f"/api/v1/platform/jobs/{job_id}/retry", headers=bearer(root))

    assert refused.status_code == 409
    assert refused.json()["code"] == "job_not_retryable"
    assert refused.json()["message"] == (
        "That task cannot be retried here. A failed marking is retried from its attempt."
    )


async def test_a_stalled_job_can_be_cancelled_but_a_live_one_cannot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    stalled = await a_job(db_session, task="produce_media", status="doing", media_id=str(uuid.uuid4()))
    await db_session.execute(
        text("UPDATE procrastinate_jobs SET worker_id = NULL WHERE id = :id"), {"id": stalled}
    )
    worker_id = (
        await db_session.execute(text("INSERT INTO procrastinate_workers DEFAULT VALUES RETURNING id"))
    ).scalar_one()
    live = await a_job(db_session, task="produce_media", status="doing", media_id=str(uuid.uuid4()))
    await db_session.execute(
        text("UPDATE procrastinate_jobs SET worker_id = :worker WHERE id = :id"),
        {"worker": worker_id, "id": live},
    )

    cancelled = await client.post(f"/api/v1/platform/jobs/{stalled}/cancel", headers=bearer(root))
    assert cancelled.status_code == 204, cancelled.text
    assert await status_of(db_session, stalled) == "aborted"
    assert await status_of(db_session, live) == "doing"

    refused = await client.post(f"/api/v1/platform/jobs/{live}/cancel", headers=bearer(root))
    assert refused.status_code == 409
    assert refused.json()["code"] == "job_not_cancellable"


async def test_only_a_platform_admin_may_act_on_jobs(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("trainee@example.com")
    job_id = await a_job(db_session, task="produce_media", status="failed", media_id=str(uuid.uuid4()))

    for action in ("retry", "cancel"):
        response = await client.post(f"/api/v1/platform/jobs/{job_id}/{action}", headers=bearer(someone))
        assert response.status_code == 403
