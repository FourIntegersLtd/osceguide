"""Reading procrastinate's own tables.

The queue's rows were written by our transactions (ADR 0006) and read by
nothing in `app/` — only the tests looked, to prove a job had been queued.
"Why has this attempt no feedback?" is answered by exactly that row, so the
platform console needs the read. One reader, in the lowest slice, so every
slice above can ask without each growing its own copy of the SQL.

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
    id: int
    queue_name: str
    task_name: str
    status: str
    attempts: int
    scheduled_at: datetime | None
    args: dict[str, Any]
    lock: str | None
    queueing_lock: str | None


def _ref(row: Any) -> JobRef:
    return JobRef(
        id=int(row.id),
        queue_name=row.queue_name,
        task_name=row.task_name,
        status=row.status,
        attempts=int(row.attempts),
        scheduled_at=row.scheduled_at,
        args=dict(row.args or {}),
        lock=row.lock,
        queueing_lock=row.queueing_lock,
    )


async def jobs_for_arg(
    session: AsyncSession, *, task_name: str, key: str, values: Sequence[str]
) -> list[JobRef]:
    """Every job of one task whose `args[key]` is one of `values`, newest first.

    This is how a job is found from the thing it is about: the scoring job
    carries `attempt_id` in its arguments and nowhere else.
    """
    if not values:
        return []
    stmt = text(
        f"SELECT {_COLUMNS} FROM procrastinate_jobs "  # noqa: S608 - column list is a constant
        "WHERE task_name = :task_name AND args->>:key = ANY(:values) ORDER BY id DESC"
    )
    rows = await session.execute(stmt, {"task_name": task_name, "key": key, "values": list(values)})
    return [_ref(row) for row in rows]


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
    return [_ref(row) for row in await session.execute(stmt, params)]


async def counts_by_status(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(text("SELECT status, count(*) AS n FROM procrastinate_jobs GROUP BY status"))
    counts = {status: 0 for status in JOB_STATUSES}
    for row in rows:
        counts[str(row.status)] = int(row.n)
    return counts


async def latest_worker_heartbeat(session: AsyncSession) -> datetime | None:
    """When a worker last said it was alive; None if none ever has."""
    return (await session.execute(text("SELECT max(last_heartbeat) FROM procrastinate_workers"))).scalar()
