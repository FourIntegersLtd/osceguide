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


async def job_by_id_locked(session: AsyncSession, job_id: int) -> JobRef | None:
    """One job by id, or None, with its row locked until the transaction ends so a worker
    cannot move it on between the console's check and its act."""
    stmt = text(f"SELECT {_COLUMNS} FROM procrastinate_jobs WHERE id = :id FOR UPDATE")  # noqa: S608
    job_row = (await session.execute(stmt, {"id": job_id})).first()
    return _ref(job_row) if job_row is not None else None


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


@dataclass(frozen=True)
class JobEventRef:
    """One row of `procrastinate_events`: what happened to a job, and when."""

    type: str
    at: datetime


async def events_by_job(session: AsyncSession, job_ids: Sequence[int]) -> dict[int, list[JobEventRef]]:
    """Each job's history, oldest first. procrastinate keeps no exception text,
    so this is all there is to say why a job failed without the worker's log."""
    if not job_ids:
        return {}
    event_rows = await session.execute(
        text("SELECT job_id, type, at FROM procrastinate_events WHERE job_id = ANY(:ids) ORDER BY id"),
        {"ids": list(job_ids)},
    )
    events: dict[int, list[JobEventRef]] = {}
    for event_row in event_rows:
        event = JobEventRef(type=str(event_row.type), at=event_row.at)
        events.setdefault(int(event_row.job_id), []).append(event)
    return events


async def stalled_jobs(session: AsyncSession, *, seconds_since_heartbeat: int) -> list[JobRef]:
    """Jobs left `doing` by a worker that died: its row pruned (`worker_id` null)
    or its heartbeat older than the limit. procrastinate's own
    `select_stalled_jobs_by_heartbeat`, read through our session."""
    stmt = text(
        f"SELECT {', '.join('job.' + column for column in _COLUMNS.split(', '))} FROM procrastinate_jobs job "  # noqa: S608
        "LEFT JOIN procrastinate_workers worker ON worker.id = job.worker_id "
        "WHERE job.status = 'doing' AND (job.worker_id IS NULL "
        "OR worker.last_heartbeat < now() - make_interval(secs => :seconds)) ORDER BY job.id"
    )
    return [_ref(job_row) for job_row in await session.execute(stmt, {"seconds": seconds_since_heartbeat})]


async def is_stalled(session: AsyncSession, job_id: int, *, seconds_since_heartbeat: int) -> bool:
    """Whether this one job is `doing` with a dead worker (see `stalled_jobs`)."""
    stmt = text(
        "SELECT 1 FROM procrastinate_jobs job "
        "LEFT JOIN procrastinate_workers worker ON worker.id = job.worker_id "
        "WHERE job.id = :id AND job.status = 'doing' AND (job.worker_id IS NULL "
        "OR worker.last_heartbeat < now() - make_interval(secs => :seconds))"
    )
    found = await session.execute(stmt, {"id": job_id, "seconds": seconds_since_heartbeat})
    return found.first() is not None


async def requeue(session: AsyncSession, job_id: int) -> None:
    """Put a stalled job back in the queue now, counting the lost run as an attempt."""
    await session.execute(
        text("SELECT procrastinate_retry_job_v2(:id, now(), NULL, NULL, NULL)"), {"id": job_id}
    )


async def fail(session: AsyncSession, job_id: int) -> None:
    """Give up on a stalled job: `failed`, kept for the console."""
    await session.execute(text("SELECT procrastinate_finish_job_v1(:id, 'failed', false)"), {"id": job_id})


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


async def waiting_with_lock(session: AsyncSession, queueing_lock: str) -> bool:
    """Whether a waiting job already holds this queueing lock (procrastinate allows one)."""
    stmt = text("SELECT 1 FROM procrastinate_jobs WHERE queueing_lock = :lock AND status = 'todo' LIMIT 1")
    return (await session.execute(stmt, {"lock": queueing_lock})).first() is not None


async def retry_failed(session: AsyncSession, job_id: int) -> None:
    """Queue a failed job again, now."""
    await session.execute(
        text("SELECT procrastinate_retry_job_v2(:id, now(), NULL, NULL, NULL)"), {"id": job_id}
    )


async def cancel_waiting(session: AsyncSession, job_id: int) -> None:
    """Stop a job that has not started: `cancelled`, kept for the console."""
    await session.execute(text("SELECT procrastinate_cancel_job_v1(:id, false, false)"), {"id": job_id})


async def cancel_running(session: AsyncSession, job_id: int) -> None:
    """Stop a job whose worker died: `aborted`, procrastinate's word for a running job stopped."""
    await session.execute(text("SELECT procrastinate_finish_job_v1(:id, 'aborted', false)"), {"id": job_id})
