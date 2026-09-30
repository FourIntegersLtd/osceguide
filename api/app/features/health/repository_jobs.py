"""Reading procrastinate's own tables.

The queue's rows were written by our transactions (ADR 0006) and read by
nothing in `app/` — only the tests looked, to prove a job had been queued.
"Why has this attempt no feedback?" is answered by exactly that row, so the
platform console needs the read. One reader here, so no other feature needs
its own copy of the SQL.

Plain `text()` rather than mapped models: the tables are procrastinate's, its
migrations own their shape, and a mapping of ours would drift from them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# procrastinate's own vocabulary; `aborting` is the pre-3.0 spelling it keeps
# in the enum for old rows.
JOB_STATUSES = ("todo", "doing", "succeeded", "failed", "cancelled", "aborting", "aborted")

_COLUMNS = "id, queue_name, task_name, status, attempts, scheduled_at, args, lock, queueing_lock"


@dataclass(frozen=True)
class JobRef:
    """One row of `procrastinate_jobs`, typed rather than read as a raw database row."""

    id: int
    queue_name: str
    task_name: str
    status: str
    attempts: int
    scheduled_at: datetime | None
    args: dict[str, Any]
    lock: str | None
    queueing_lock: str | None


def _ref(job_row: Any) -> JobRef:
    """Turn one raw row from `procrastinate_jobs` into a typed `JobRef`."""
    return JobRef(
        id=int(job_row.id),
        queue_name=job_row.queue_name,
        task_name=job_row.task_name,
        status=job_row.status,
        attempts=int(job_row.attempts),
        scheduled_at=job_row.scheduled_at,
        args=dict(job_row.args or {}),
        lock=job_row.lock,
        queueing_lock=job_row.queueing_lock,
    )


async def jobs_for_arg(
    session: AsyncSession, *, task_name: str, key: str, matching_values: Sequence[str]
) -> list[JobRef]:
    """Every job of one task whose `args[key]` is one of `matching_values`, newest first.

    This is how a job is found from the thing it is about: the scoring job
    carries `attempt_id` in its arguments and nowhere else.
    """
    if not matching_values:
        return []
    stmt = text(
        f"SELECT {_COLUMNS} FROM procrastinate_jobs "  # noqa: S608 - column list is a constant
        "WHERE task_name = :task_name AND args->>:key = ANY(:values) ORDER BY id DESC"
    )
    job_rows = await session.execute(
        stmt, {"task_name": task_name, "key": key, "values": list(matching_values)}
    )
    return [_ref(job_row) for job_row in job_rows]


async def list_jobs(
    session: AsyncSession,
    *,
    status: str | None,
    task_name: str | None,
    before_id: int | None,
    limit: int,
) -> list[JobRef]:
    """A page of the queue, newest first, keyed on the job id."""
    clauses = ["TRUE"]
    params: dict[str, Any] = {"limit": limit}
    if status is not None:
        clauses.append("status = :status")
        params["status"] = status
    if task_name is not None:
        clauses.append("task_name = :task_name")
        params["task_name"] = task_name
    if before_id is not None:
        clauses.append("id < :before_id")
        params["before_id"] = before_id
    stmt = text(
        f"SELECT {_COLUMNS} FROM procrastinate_jobs WHERE {' AND '.join(clauses)} "  # noqa: S608
        "ORDER BY id DESC LIMIT :limit"
    )
    return [_ref(job_row) for job_row in await session.execute(stmt, params)]


async def counts_by_status(session: AsyncSession) -> dict[str, int]:
    """How many jobs sit in each status, including the statuses that currently have none."""
    status_rows = await session.execute(
        text("SELECT status, count(*) AS n FROM procrastinate_jobs GROUP BY status")
    )
    counts = {status: 0 for status in JOB_STATUSES}
    for status_row in status_rows:
        counts[str(status_row.status)] = int(status_row.n)
    return counts


async def latest_worker_heartbeat(session: AsyncSession) -> datetime | None:
    """When a worker last said it was alive; None if none ever has."""
    return (await session.execute(text("SELECT max(last_heartbeat) FROM procrastinate_workers"))).scalar()
