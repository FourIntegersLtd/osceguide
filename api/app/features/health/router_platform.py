"""The platform console's view of the machinery. `PlatformAdmin` only.

`/health` is public and says whether the platform is up. These say whether it
is *working*: what the queue holds, whether a worker has been seen, and which
jobs failed — the row a support question about a missing feedback ends at.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.core.db import SessionDep as Session
from app.core.db import SessionOpenerDep
from app.core.errors import Forbidden, error_responses
from app.core.events import get_event_bus
from app.core.openapi import sse_responses
from app.core.ports import ClockDep, EventBus
from app.core.redis import get_redis
from app.core.settings import SettingsDep
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.core.tenancy import PlatformAdmin
from app.features.health import schemas, service
from app.features.health.errors import JobNotCancellable, JobNotFound, JobNotRetryable, MessageNotRetryable

router = APIRouter(tags=["health"])


STATUS_PATTERN = "^(todo|doing|succeeded|failed|cancelled|aborting|aborted)$"


@router.get(
    "/platform/health",
    response_model=schemas.PlatformHealth,
    responses=error_responses(Forbidden),
)
async def read_platform_health(admin: PlatformAdmin, session: Session) -> schemas.PlatformHealth:
    """The liveness report, the queue by status, and when a worker last checked in."""
    _ = admin
    return await service.platform_health(session, get_redis())


@router.get(
    "/platform/jobs",
    response_model=schemas.JobsPage,
    responses=error_responses(Forbidden),
)
async def list_jobs(
    admin: PlatformAdmin,
    session: Session,
    status: Annotated[str | None, Query(pattern=STATUS_PATTERN)] = None,
    task: Annotated[str | None, Query(description="A task name, such as `score_attempt`")] = None,
    before_id: Annotated[int | None, Query(ge=1, description="Continue from a previous page")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> schemas.JobsPage:
    """The queue, newest first. `status=failed` is what to look at when something is missing.

    A failed marking is re-queued through its attempt —
    `POST /platform/attempts/{id}/rescore` — so the retry is checked against the
    current state rather than replayed blind; any other failed task is retried below.
    """
    _ = admin
    return await service.list_jobs(session, status=status, task_name=task, before_id=before_id, limit=limit)


@router.post(
    "/platform/jobs/{job_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, JobNotFound, JobNotRetryable),
)
async def retry_job(job_id: int, admin: PlatformAdmin, session: Session, clock: ClockDep) -> None:
    """Queue a failed task again. `job_not_retryable` for a marking (retry it from its
    attempt), for a task that is not failed, or when the same task is already waiting."""
    await service.retry_job(session, job_id, actor=admin, now=clock.now())


@router.post(
    "/platform/jobs/{job_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, JobNotFound, JobNotCancellable),
)
async def cancel_job(job_id: int, admin: PlatformAdmin, session: Session, clock: ClockDep) -> None:
    """Cancel a waiting task, or a running one whose worker stopped reporting. A task
    a live worker is still running is `job_not_cancellable`."""
    await service.cancel_job(session, job_id, actor=admin, now=clock.now())


@router.get(
    "/platform/machinery",
    response_model=schemas.Machinery,
    responses=error_responses(Forbidden),
)
async def read_machinery(
    admin: PlatformAdmin,
    session: Session,
    settings: SettingsDep,
    status: Annotated[
        str | None, Query(pattern=STATUS_PATTERN, description="Which tab of the queue to send")
    ] = None,
) -> schemas.Machinery:
    """The machinery page in one read; its stream sends this same shape whenever it changes."""
    _ = admin
    return await service.machinery(session, get_redis(), settings, job_status=status)


@router.get(
    "/platform/machinery/stream",
    responses=sse_responses(schemas.Machinery, Forbidden),
    # Checked in the handler (a stream cannot take `require_org`), so stated here.
    openapi_extra={"x-capability": "platform_admin"},
    response_class=StreamingResponse,
)
async def stream_machinery(
    principal: StreamPrincipal,
    settings: SettingsDep,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
    status: Annotated[
        str | None, Query(pattern=STATUS_PATTERN, description="Which tab of the queue to send")
    ] = None,
) -> StreamingResponse:
    """The machinery page, live: health, voice capacity and the queue, re-sent as they change."""
    if not principal.is_platform_admin:
        raise Forbidden()
    return StreamingResponse(
        service.machinery_stream(
            job_status=status, open_session=open_session, redis=get_redis(), settings=settings, bus=bus
        ),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


@router.get(
    "/platform/outbox/undelivered",
    response_model=schemas.UndeliveredMail,
    responses=error_responses(Forbidden),
)
async def list_undelivered_mail(admin: PlatformAdmin, session: Session) -> schemas.UndeliveredMail:
    """Email the outbox abandoned after its last attempt: an invitation,
    a reset or a receipt that never left. Newest first, one page, with
    `has_more` when older ones were left off."""
    _ = admin
    return await service.undelivered_mail(session)


@router.post(
    "/platform/outbox/{message_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Forbidden, MessageNotRetryable),
)
async def retry_undelivered_mail(
    message_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> None:
    """Queue an abandoned email again with a fresh set of attempts.
    `message_not_retryable` when it is no longer abandoned, so a second press
    never sends it twice."""
    await service.retry_mail(session, message_id, actor=admin, now=clock.now())
