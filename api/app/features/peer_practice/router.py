"""The waiting room: joining it, reading it, watching it, leaving it."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import AudienceNotYours, InvalidAudience
from app.core.auth import CurrentPrincipal
from app.core.db import SessionOpenerDep, get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.events import get_event_bus
from app.core.openapi import sse_responses
from app.core.ports import ClockDep, EventBus
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.features.peer_practice import errors, schemas, service, service_stream

router = APIRouter(tags=["peer-practice"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/peer-practice/queue",
    response_model=schemas.QueueStatus,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        errors.UnknownExamError, errors.NotEntitled, Unauthenticated, InvalidAudience, AudienceNotYours
    ),
)
async def join_queue(
    body: schemas.JoinQueue, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.QueueStatus:
    """Joining twice returns the place you already hold rather than a second one."""
    return await service.join_queue(
        session,
        user_id=principal.user_id,
        exam_code=body.exam_code,
        now=clock.now(),
        audience=body.audience.to_audience(),
    )


# One queue entry's current status.
@router.get(
    "/peer-practice/queue/{entry_id}",
    response_model=schemas.QueueStatus,
    responses=error_responses(Unauthenticated, errors.QueueEntryNotFound),
)
async def read_status(
    entry_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.QueueStatus:
    return await service.read_status(session, entry_id, user_id=principal.user_id)


# Pushes this caller's own queue status until it stops being "waiting".
@router.get(
    "/peer-practice/queue/{entry_id}/stream",
    responses=sse_responses(schemas.QueueStatus, Unauthenticated, errors.QueueEntryNotFound),
    response_class=StreamingResponse,
)
async def stream_status(
    entry_id: uuid.UUID,
    principal: StreamPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
) -> StreamingResponse:
    return StreamingResponse(
        service_stream.queue_stream(entry_id, principal.user_id, bus=bus, open_session=open_session),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


# Give up a queue place. Refused if it was already matched or already left.
@router.delete(
    "/peer-practice/queue/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.QueueEntryNotFound),
)
async def leave_queue(
    entry_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> Response:
    await service.leave_queue(session, entry_id, user_id=principal.user_id, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
