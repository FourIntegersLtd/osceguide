"""The console's view of the machinery: the queue, the worker, the Cloud cap."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def queued(db_session: AsyncSession, *, task: str = "score_attempt", **args: str) -> None:
    await defer_in_transaction(db_session, queue="scoring", task=task, queueing_lock=None, args=args)


async def test_the_queue_is_listed_newest_first_and_narrowed_by_status_and_task(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    root = await make_actor("root@osceguide.com", platform_admin=True)
    ids = [str(uuid.uuid4()) for _ in range(3)]
    for attempt_id in ids:
        await queued(db_session, attempt_id=attempt_id)
    await queued(db_session, task="deliver_outbound_messages", batch="x")
    await db_session.execute(
        text("UPDATE procrastinate_jobs SET status = 'failed' WHERE args->>'attempt_id' = :id"),
        {"id": ids[0]},
    )
    await db_session.flush()

    failed = await client.get("/api/v1/platform/jobs?status=failed", headers=bearer(root))
    assert failed.status_code == 200, failed.text
    assert [job["args"]["attempt_id"] for job in failed.json()["items"]] == [ids[0]]

    first = await client.get("/api/v1/platform/jobs?task=score_attempt&limit=2", headers=bearer(root))
    assert [job["args"]["attempt_id"] for job in first.json()["items"]] == [ids[2], ids[1]]
    assert first.json()["next_before_id"]
    rest = await client.get(
        f"/api/v1/platform/jobs?task=score_attempt&before_id={first.json()['next_before_id']}",
        headers=bearer(root),
    )
    assert ids[0] in [job["args"]["attempt_id"] for job in rest.json()["items"]]
    assert all(job["task_name"] == "score_attempt" for job in rest.json()["items"])
    assert (await client.get("/api/v1/platform/jobs?status=lost", headers=bearer(root))).status_code == 422


async def test_platform_health_counts_the_queue_and_says_when_a_worker_was_last_seen(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await queued(db_session, attempt_id=str(uuid.uuid4()))
    await db_session.flush()

    health = await client.get("/api/v1/platform/health", headers=bearer(root))
    assert health.status_code == 200, health.text
    body = health.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["jobs_by_status"]["todo"] >= 1
    assert set(body["jobs_by_status"]) >= {"todo", "doing", "succeeded", "failed"}
    assert body["worker_seen_at"] is None, "no worker has run in the test database"


async def test_cloud_capacity_is_a_count_not_a_reservation(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    capacity = await client.get("/api/v1/platform/voice/capacity", headers=bearer(root))
    assert capacity.status_code == 200, capacity.text
    body = capacity.json()
    assert body["max_concurrent"] >= 1
    # Redis is disabled under test, so the count cannot be given — and says so
    # rather than pretending the cap is empty.
    assert body["active"] is None
    assert body["free"] is None


async def test_the_machinery_is_refused_to_anybody_but_a_platform_admin(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("someone@example.com")
    for path in ("/api/v1/platform/jobs", "/api/v1/platform/health", "/api/v1/platform/voice/capacity"):
        assert (await client.get(path, headers=bearer(someone))).status_code == 403, path
