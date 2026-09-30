"""Reading the queue back: the rows our transactions wrote, found by what they are about."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import defer_in_transaction
from app.features.health import repository_jobs

pytestmark = pytest.mark.db


async def test_a_job_is_found_by_the_thing_it_is_about(db_session: AsyncSession) -> None:
    attempt_id = str(uuid.uuid4())
    await defer_in_transaction(
        db_session,
        queue="scoring",
        task="score_attempt",
        queueing_lock=f"score:{attempt_id}:v1",
        args={"attempt_id": attempt_id, "policy_version": "v1"},
    )

    found = await repository_jobs.jobs_for_arg(
        db_session, task_name="score_attempt", key="attempt_id", matching_values=[attempt_id, "not-a-job"]
    )
    [job] = found
    assert job.status == "todo"
    assert job.attempts == 0
    assert job.args["policy_version"] == "v1"
    assert job.queueing_lock == f"score:{attempt_id}:v1"
    assert (
        await repository_jobs.jobs_for_arg(
            db_session, task_name="score_attempt", key="attempt_id", matching_values=[]
        )
        == []
    )


async def test_the_queue_is_listed_newest_first_and_counted(db_session: AsyncSession) -> None:
    ids = [str(uuid.uuid4()) for _ in range(2)]
    for attempt_id in ids:
        await defer_in_transaction(
            db_session,
            queue="scoring",
            task="score_attempt",
            queueing_lock=None,
            args={"attempt_id": attempt_id},
        )

    page = await repository_jobs.list_jobs(
        db_session, status="todo", task_name="score_attempt", before_id=None, limit=1
    )
    assert [job.args["attempt_id"] for job in page] == [ids[1]]
    older = await repository_jobs.list_jobs(
        db_session, status="todo", task_name="score_attempt", before_id=page[0].id, limit=10
    )
    assert ids[0] in [job.args["attempt_id"] for job in older]

    counts = await repository_jobs.counts_by_status(db_session)
    assert counts["todo"] >= 2
    assert set(counts) == set(repository_jobs.JOB_STATUSES)
    assert await repository_jobs.latest_worker_heartbeat(db_session) is None
