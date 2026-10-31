"""Checking whether the platform is up, and answering the platform console's questions about it."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core import observability
from app.core.auth import Principal
from app.core.db import SessionOpener, savepoint
from app.core.events import voice_queue_topic
from app.core.logging import get_logger
from app.core.ports import EventBus
from app.core.settings import Settings, get_settings
from app.core.sse import Snapshot, event_stream
from app.features.attempts import service as attempts_service
from app.features.attempts.jobs import SCORING_TASK, record_marking_gave_up
from app.features.health import repository, repository_jobs, repository_size, service_size
from app.features.health.errors import JobNotCancellable, JobNotFound, JobNotRetryable, MessageNotRetryable
from app.features.health.repository_jobs import JobEventRef, JobRef
from app.features.health.schemas import (
    CheckState,
    DatabaseSizeRead,
    HealthResponse,
    JobEventRead,
    JobRead,
    JobsPage,
    Machinery,
    MachineryCapacity,
    PlatformHealth,
    UndeliveredMail,
    UndeliveredMessage,
)
from app.features.notifications import service as notifications
from app.features.tenancy import service_audit
from app.features.voice import service as voice_service

log = get_logger(__name__)
T = TypeVar("T")
CHECK_TIMEOUT_SECONDS = 2.0
# The size read is limited by the server, not by cancelling it; this only stops a server that never answers.
SIZE_BACKSTOP_SECONDS = 5.0
# The checks whose failure leaves the platform up but degraded; a failed database is `down`.
DEGRADING = ("redis", "content")
# How often the machinery stream re-reads what changes with nobody announcing
# it: a job finishing, a worker's heartbeat, a Cloud slot lapsing.
MACHINERY_REFRESH_SECONDS = 5.0
MACHINERY_JOB_PAGE = 100
# A worker beats every 10s by default; three minutes of silence is a dead one,
# not a slow one, and `worker_id` is null once procrastinate prunes it.
STALLED_AFTER_SECONDS = 180
# A stalled job is put back up to three times. procrastinate counts each requeue in the job's
# `attempts`, so the count survives a restart. A fourth stall is likely the job itself taking its
# worker down, so it fails rather than looping.
MAX_STALLED_REQUEUES = 3


async def _answers_in_time(
    name: str, query: Awaitable[T], *, timeout: float = CHECK_TIMEOUT_SECONDS
) -> T | None:
    """What a check's query returns within the timeout, or None when it fails; never raises."""
    try:
        return await asyncio.wait_for(query, timeout)
    except Exception as exc:  # noqa: BLE001 - health must never raise
        log.warning("health check failed", check=name, error=str(exc))
        return None


async def check_database(session: AsyncSession) -> CheckState:
    """Whether the database answers a trivial query within the timeout."""
    return "ok" if await _answers_in_time("database", repository.ping(session)) is not None else "error"


async def check_content(session: AsyncSession) -> CheckState:
    """Whether every published platform station is bound to a template (else it has no written brief)."""
    unbound = await _answers_in_time("content", repository.unbound_platform_stations(session))
    return "ok" if unbound == 0 else "error"


async def check_redis(redis: Redis | None) -> CheckState:
    """Whether Redis answers within the timeout, or `disabled` when this deployment has none."""
    if redis is None:
        return "disabled"
    return "ok" if await _answers_in_time("redis", redis.ping()) is not None else "error"


async def health_report(session: AsyncSession, redis: Redis | None) -> HealthResponse:
    """The public health check: `down` if the database fails, `degraded` if Redis fails or a published
    platform station has no template (`content`), else `ok`."""
    database = await check_database(session)
    # With the database down the content query is not run (it would only fail on a broken session),
    # so `content` reads "error" without having been checked.
    content = await check_content(session) if database == "ok" else "error"
    checks = {"database": database, "redis": await check_redis(redis), "content": content}
    if database == "error":
        status = "down"
    elif any(checks[name] == "error" for name in DEGRADING):
        status = "degraded"
    else:
        status = "ok"
    return HealthResponse(
        status=status, version=__version__, commit=get_settings().git_commit_sha, checks=checks
    )


# --- What the console asks about the platform's own machinery.


async def _measured_size(session: AsyncSession) -> DatabaseSizeRead:
    """The database's size; raises if the server gives up on it after `CHECK_TIMEOUT_SECONDS`.

    The session is shared with the checks around it, so the time limit is the server's
    (`statement_timeout`), not an asyncio cancel: abandoning a query mid-flight on a shared connection
    leaves it unusable for every statement after. A savepoint takes the failed statement's error,
    and the limit with it.
    """
    async with savepoint(session):
        await repository_size.limit_statement_time(session, seconds=CHECK_TIMEOUT_SECONDS)
        size = await service_size.database_size(session, now=datetime.now(UTC))
        await repository_size.restore_statement_time(session)
        return size


async def platform_health(session: AsyncSession, redis: Redis | None) -> PlatformHealth:
    """The public health report, plus the queue's counts by status, when a worker last checked in and how
    full the database is.

    The size is measured now, not read from the daily task's history, so it is there with no worker running.
    When it cannot be read it is left out and the rest of the report stands.
    """
    report = await health_report(session, redis)
    return PlatformHealth(
        **report.model_dump(),
        jobs_by_status=await repository_jobs.counts_by_status(session),
        worker_seen_at=await repository_jobs.latest_worker_heartbeat(session),
        database_size=await _answers_in_time(
            "database_size", _measured_size(session), timeout=CHECK_TIMEOUT_SECONDS + SIZE_BACKSTOP_SECONDS
        ),
    )


# Six missed beats and the board says the worker is down.
WORKER_MISSED_BEATS = 6


async def worker_running(session: AsyncSession, *, now: datetime) -> bool:
    """Whether a job worker has checked in lately (S-7), by the worker's own heartbeat interval."""
    seen = await repository_jobs.latest_worker_heartbeat(session)
    stale_after = timedelta(seconds=WORKER_MISSED_BEATS * get_settings().worker_heartbeat_seconds)
    return seen is not None and now - seen < stale_after


async def list_jobs(
    session: AsyncSession,
    *,
    status: str | None,
    task_name: str | None,
    before_id: int | None,
    limit: int,
) -> JobsPage:
    """A page of the queue for the platform console, newest first."""
    jobs = await repository_jobs.list_jobs(
        session, status=status, task_name=task_name, before_id=before_id, limit=limit + 1
    )
    page = jobs[:limit]
    events = await repository_jobs.events_by_job(session, [job.id for job in page])
    return JobsPage(
        items=[_read(job, events.get(job.id, [])) for job in page],
        next_before_id=page[-1].id if len(jobs) > limit else None,
    )


async def machinery(
    session: AsyncSession, redis: Redis | None, settings: Settings, *, job_status: str | None
) -> Machinery:
    """The whole machinery page at this moment: health, voice capacity and one status of the queue."""
    capacity = await voice_service.cloud_capacity(settings)
    return Machinery(
        health=await platform_health(session, redis),
        capacity=MachineryCapacity.model_validate(capacity.model_dump()),
        jobs=await list_jobs(
            session, status=job_status, task_name=None, before_id=None, limit=MACHINERY_JOB_PAGE
        ),
        job_status=job_status,
    )


def machinery_stream(
    *,
    job_status: str | None,
    open_session: SessionOpener,
    redis: Redis | None,
    settings: Settings,
    bus: EventBus,
) -> AsyncIterator[str]:
    """The machinery page, pushed: health, voice capacity and one tab of the queue.

    Woken at once when a voice seat is freed, and re-read every few seconds as
    well, because the queue and the worker's heartbeat change in procrastinate's
    tables with no event on the bus. The browser only listens; it never polls.
    """

    async def snapshot() -> Snapshot:
        """One frame of the whole page, read in its own short transaction."""
        async with open_session() as session:
            page = await machinery(session, redis, settings, job_status=job_status)
        return Snapshot(page.model_dump_json())

    return event_stream(
        topics=[voice_queue_topic()],
        snapshot=snapshot,
        bus=bus,
        heartbeat_seconds=MACHINERY_REFRESH_SECONDS,
        snapshot_on_heartbeat=True,
    )


async def reclaim_stalled_jobs(session: AsyncSession) -> tuple[list[int], list[int]]:
    """Move on every job a dead worker left `doing`: requeued up to `MAX_STALLED_REQUEUES` times,
    failed after that with the reason in the platform audit log.

    procrastinate prunes a dead worker but leaves its jobs `doing` for ever, which
    is how two `produce_media` runs sat at 0 attempts. Returns `(requeued, failed)` ids.
    """
    requeued: list[int] = []
    failed: list[int] = []
    for job in await repository_jobs.stalled_jobs(session, seconds_since_heartbeat=STALLED_AFTER_SECONDS):
        if job.attempts < MAX_STALLED_REQUEUES:
            await repository_jobs.requeue(session, job.id)
            requeued.append(job.id)
        else:
            await repository_jobs.fail(session, job.id)
            failed.append(job.id)
            await service_audit.record_system(
                session,
                action="job.stalled_failed",
                target_type="job",
                target_id=str(job.id),
                summary=f"{job.task_name} lost its worker {job.attempts + 1} times and was failed",
                meta={"task": job.task_name, "requeues": job.attempts},
            )
            if job.task_name == SCORING_TASK:
                # The job will not run again, so the attempt has to say marking gave up.
                await record_marking_gave_up(session, uuid.UUID(job.args["attempt_id"]))
    return requeued, failed


async def abandon_stale_attempts(session: AsyncSession, *, now: datetime) -> list[uuid.UUID]:
    """The sweep's second step: fail the consumer attempts nobody finished (S-25)."""
    return await attempts_service.abandon_stale_attempts(session, now=now)


async def _run_recorded(
    opener: SessionOpener, name: str, step: Callable[[AsyncSession], Awaitable[T]], *, now: datetime
) -> T | None:
    """Run one step in its own transaction. A step that raises is rolled back and written to the platform
    audit log (`sweep.failed`), where staff read it, instead of only the process log. Returns what the step
    returned once its transaction has committed, None if it failed."""
    try:
        async with opener() as session:
            result = await step(session)
        return result
    except Exception as exc:  # noqa: BLE001 - a failing step must not stop the next, and is recorded
        log.error("sweep step failed", step=name, error=str(exc))
        async with opener() as session:
            await service_audit.record_system(
                session,
                action="sweep.failed",
                target_type="sweep",
                target_id=name,
                summary=f"{name} failed: {exc}",
                meta={"error": f"{type(exc).__name__}: {exc}"},
                at=now,
            )
        return None


async def run_sweep(opener: SessionOpener, *, now: datetime) -> None:
    """Run each step of the five-minute sweep in its own transaction.

    A step that raises is rolled back and written to the platform audit log (`sweep.failed`), where
    staff read it, then the next step still runs. Before this a failure reached the log and nothing else.
    """
    steps = (
        ("reclaim_stalled_jobs", lambda session: reclaim_stalled_jobs(session)),
        ("abandon_stale_attempts", lambda session: abandon_stale_attempts(session, now=now)),
    )
    for name, step in steps:
        await _run_recorded(opener, name, step, now=now)


async def run_size_check(opener: SessionOpener, *, now: datetime) -> None:
    """The daily size reading; a failure is written to the platform audit log like the sweep's.

    A person is paged only after the reading has committed, so a commit that fails and is run again
    pages once, not twice.
    """
    page = await _run_recorded(
        opener,
        "record_database_size",
        lambda session: service_size.record_database_size(session, now=now),
        now=now,
    )
    if page:
        observability.report_message(page, level="error")


async def prune_job_history(
    session: AsyncSession, delete_old_jobs: Callable[..., Awaitable[None]], *, now: datetime
) -> None:
    """Have procrastinate delete succeeded jobs past the retention, and record how many went.

    The library's own delete does the work; deleting a job takes its events with it (`ON DELETE CASCADE`),
    and the periodic-defer rows it leaves are pruned by procrastinate on its next tick. It returns no
    count, so the jobs it will remove are counted first.
    """
    days = get_settings().job_history_retention_days
    removed = await repository_jobs.succeeded_jobs_before(session, now - timedelta(days=days))
    await delete_old_jobs(nb_hours=days * 24)
    if removed:
        await service_audit.record_system(
            session,
            action="jobs.pruned",
            target_type="job",
            target_id="history",
            summary=(
                f"Removed {removed} succeeded {'job' if removed == 1 else 'jobs'} "
                f"and their events older than {days} days."
            ),
            meta={"removed": removed, "older_than_days": days},
            at=now,
        )


async def run_job_pruning(
    opener: SessionOpener, *, delete_old_jobs: Callable[..., Awaitable[None]], now: datetime
) -> None:
    """The daily queue clean-up; a failure is written to the platform audit log like the sweep's."""
    await _run_recorded(
        opener,
        "prune_job_history",
        lambda session: prune_job_history(session, delete_old_jobs, now=now),
        now=now,
    )


async def retry_job(session: AsyncSession, job_id: int, *, actor: Principal, now: datetime) -> None:
    """Queue a failed task again. A marking is not replayed blind: it goes back through
    its attempt, so the retry is checked against the attempt's state."""
    job = await repository_jobs.job_by_id_locked(session, job_id)
    if job is None:
        raise JobNotFound()
    if job.status != "failed" or job.task_name == SCORING_TASK:
        raise JobNotRetryable()
    if job.queueing_lock and await repository_jobs.waiting_with_lock(session, job.queueing_lock):
        raise JobNotRetryable("The same task is already waiting to run.")
    await repository_jobs.retry_failed(session, job_id)
    await service_audit.record(
        session, actor=actor, action="job.retried", target_type="job", target_id=str(job_id), at=now
    )


async def cancel_job(session: AsyncSession, job_id: int, *, actor: Principal, now: datetime) -> None:
    """Stop a waiting task, or a running one whose worker has gone quiet. A task a live
    worker is still running is left alone."""
    job = await repository_jobs.job_by_id_locked(session, job_id)
    if job is None:
        raise JobNotFound()
    if job.status == "todo":
        await repository_jobs.cancel_waiting(session, job_id)
    elif job.status == "doing" and await repository_jobs.is_stalled(
        session, job_id, seconds_since_heartbeat=STALLED_AFTER_SECONDS
    ):
        await repository_jobs.cancel_running(session, job_id)
    else:
        raise JobNotCancellable()
    if job.task_name == SCORING_TASK:
        # The job will not run, so the attempt has to say marking gave up.
        await record_marking_gave_up(session, uuid.UUID(job.args["attempt_id"]))
    await service_audit.record(
        session, actor=actor, action="job.cancelled", target_type="job", target_id=str(job_id), at=now
    )


def _read(job: JobRef, events: list[JobEventRef]) -> JobRead:
    """Turn one job reference into the shape the platform console reads."""
    return JobRead(
        id=job.id,
        queue_name=job.queue_name,
        task_name=job.task_name,
        status=job.status,
        attempts=job.attempts,
        scheduled_at=job.scheduled_at,
        args=job.args,
        queueing_lock=job.queueing_lock,
        events=[JobEventRead(type=event.type, at=event.at) for event in events],
    )


# --- Mail the outbox gave up on. The queue is `notifications`'; this is
# the console's view of it and its one action, recorded like every platform act.


# The console lists this many; a longer outage says so rather than scrolling.
UNDELIVERED_PAGE = 100


async def undelivered_mail(session: AsyncSession) -> UndeliveredMail:
    """The newest abandoned emails, most recent first, and whether there are more."""
    found = await notifications.list_undelivered(session, limit=UNDELIVERED_PAGE + 1)
    return UndeliveredMail(
        messages=[
            UndeliveredMessage(
                id=message.id,
                recipient=message.recipient,
                subject=message.subject,
                template_key=message.template_key,
                attempts=message.attempts,
                last_error=message.last_error,
                abandoned_at=message.updated_at,
            )
            for message in found[:UNDELIVERED_PAGE]
        ],
        has_more=len(found) > UNDELIVERED_PAGE,
    )


async def retry_mail(
    session: AsyncSession, message_id: uuid.UUID, *, actor: Principal, now: datetime
) -> None:
    """Queue an abandoned email again with a fresh set of attempts, and record
    who did. Refuses `message_not_retryable` once it is not abandoned, so a
    second press never sends it twice."""
    if not await notifications.retry_undelivered(session, message_id, now=now):
        raise MessageNotRetryable()
    await service_audit.record(
        session,
        actor=actor,
        action="notifications.message_retried",
        target_type="outbound_message",
        target_id=str(message_id),
        at=now,
    )
