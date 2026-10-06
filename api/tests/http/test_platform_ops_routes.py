"""The console's view of the machinery: the queue, the worker, the Cloud cap."""

from __future__ import annotations

import asyncio
import json
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
    assert body["self_hosted_seats_taken"] is None
    assert body["queue_length"] is None


async def test_the_machinery_is_refused_to_anybody_but_a_platform_admin(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("someone@example.com")
    for path in ("/api/v1/platform/jobs", "/api/v1/platform/health", "/api/v1/platform/voice/capacity"):
        assert (await client.get(path, headers=bearer(someone))).status_code == 403, path


async def test_the_machinery_page_is_pushed_as_one_snapshot(
    streaming_client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The page loads once and then listens: health, capacity and the asked-for tab arrive together."""
    from tests.http.test_streams import frames

    root = await make_actor("root@osceguide.com", platform_admin=True)
    attempt_id = str(uuid.uuid4())
    await queued(db_session, attempt_id=attempt_id)
    await db_session.commit()

    async with streaming_client.stream(
        "GET", "/api/v1/platform/machinery/stream?status=todo", headers=bearer(root)
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        received = await asyncio.wait_for(frames(response.aiter_lines(), 2), timeout=10)

    assert [event for event, _ in received] == ["connected", "snapshot"]
    body = json.loads(received[1][1])
    assert body["health"]["checks"]["database"] == "ok"
    assert body["health"]["jobs_by_status"]["todo"] >= 1
    assert body["capacity"]["active"] is None
    assert attempt_id in [job["args"].get("attempt_id") for job in body["jobs"]["items"]]


async def test_the_machinery_stream_is_refused_to_anybody_but_a_platform_admin(
    streaming_client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("someone@example.com")
    async with streaming_client.stream(
        "GET", "/api/v1/platform/machinery/stream", headers=bearer(someone)
    ) as response:
        assert response.status_code == 403


async def test_a_job_its_worker_died_on_is_requeued_once_then_failed_with_its_history(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """B32: two produce_media jobs sat `doing` at 0 attempts after their worker
    was pruned, and a failed job said nothing about how it got there."""
    from sqlalchemy import text

    from app.features.health.service import reclaim_stalled_jobs

    root = await make_actor("root@osceguide.com", platform_admin=True)
    media_id = str(uuid.uuid4())
    await queued(db_session, task="produce_media", media_id=media_id)
    job_id = (
        await db_session.execute(
            text("SELECT id FROM procrastinate_jobs WHERE args->>'media_id' = :id"), {"id": media_id}
        )
    ).scalar_one()

    async def dies_while_running() -> None:
        await db_session.execute(
            text("UPDATE procrastinate_jobs SET status = 'doing', worker_id = NULL WHERE id = :id"),
            {"id": job_id},
        )

    async def state() -> tuple[str, int]:
        found = await db_session.execute(
            text("SELECT status, attempts FROM procrastinate_jobs WHERE id = :id"), {"id": job_id}
        )
        status, attempts = found.one()
        return str(status), int(attempts)

    await dies_while_running()
    assert job_id in (await reclaim_stalled_jobs(db_session))[0]
    assert await state() == ("todo", 1)

    await dies_while_running()
    assert job_id in (await reclaim_stalled_jobs(db_session))[1]
    assert await state() == ("failed", 2)

    failed = await client.get("/api/v1/platform/jobs?status=failed&task=produce_media", headers=bearer(root))
    assert failed.status_code == 200, failed.text
    [job] = [job for job in failed.json()["items"] if job["id"] == job_id]
    assert [event["type"] for event in job["events"]] == [
        "deferred",
        "started",
        "scheduled",  # procrastinate's retry sets a retry time, which logs as scheduled
        "deferred_for_retry",
        "started",
        "failed",
    ]
