"""Checking whether the platform is up, and answering the platform console's questions about it."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.auth import Principal
from app.core.db import SessionOpener
from app.core.events import voice_queue_topic
from app.core.logging import get_logger
from app.core.ports import EventBus
from app.core.settings import Settings, get_settings
from app.core.sse import Snapshot, event_stream
from app.features.attempts.jobs import SCORING_TASK, record_marking_gave_up
from app.features.health import repository, repository_jobs
from app.features.health.errors import JobNotCancellable, JobNotFound, JobNotRetryable, MessageNotRetryable
from app.features.health.repository_jobs import JobEventRef, JobRef
from app.features.health.schemas import (
    CheckState,
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
CHECK_TIMEOUT_SECONDS = 2.0
# How often the machinery stream re-reads what changes with nobody announcing
# it: a job finishing, a worker's heartbeat, a Cloud slot lapsing.
MACHINERY_REFRESH_SECONDS = 5.0
MACHINERY_JOB_PAGE = 100
# A worker beats every 10s by default; three minutes of silence is a dead one,
# not a slow one, and `worker_id` is null once procrastinate prunes it.
STALLED_AFTER_SECONDS = 180
# A stalled job is put back once. A second stall is likely the job itself
# taking its worker down, so it fails rather than looping.
MAX_STALLED_REQUEUES = 1


async def check_database(session: AsyncSession) -> CheckState:
    """Whether the database answers a trivial query within the timeout."""
    try:
        await asyncio.wait_for(repository.ping(session), CHECK_TIMEOUT_SECONDS)
        return "ok"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        log.warning("database check failed", error=str(exc))
        return "error"


async def check_redis(redis: Redis | None) -> CheckState:
    """Whether Redis answers within the timeout, or `disabled` when this deployment has none."""
    if redis is None:
        return "disabled"
    try:
        await asyncio.wait_for(redis.ping(), CHECK_TIMEOUT_SECONDS)
        return "ok"
    except Exception as exc:  # noqa: BLE001
        log.warning("redis check failed", error=str(exc))
        return "error"


async def health_report(session: AsyncSession, redis: Redis | None) -> HealthResponse:
    """The public health check: `down` if the database fails, `degraded` if only Redis does, else `ok`."""
    checks = {"database": await check_database(session), "redis": await check_redis(redis)}
    if checks["database"] == "error":
        status = "down"
    elif checks["redis"] == "error":
        status = "degraded"
    else:
        status = "ok"
    return HealthResponse(
        status=status, version=__version__, commit=get_settings().git_commit_sha, checks=checks
    )


# --- What the console asks about the platform's own machinery.


async def platform_health(session: AsyncSession, redis: Redis | None) -> PlatformHealth:
    """The public health report, plus the queue's counts by status and when a worker last checked in."""
    report = await health_report(session, redis)
    return PlatformHealth(
        **report.model_dump(),
        jobs_by_status=await repository_jobs.counts_by_status(session),
        worker_seen_at=await repository_jobs.latest_worker_heartbeat(session),
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
    """Move on every job a dead worker left `doing`: requeued once, failed after that.

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
            if job.task_name == SCORING_TASK:
                # The job will not run again, so the attempt has to say marking gave up.
                await record_marking_gave_up(session, uuid.UUID(job.args["attempt_id"]))
    return requeued, failed


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
