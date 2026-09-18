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
from app.core.pagination import Page
from app.core.ports import ClockDep, EventBus, VoiceTokens
from app.core.settings import SettingsDep
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.features.peer_practice import errors, schemas, service, service_stream

router = APIRouter(tags=["peer-practice"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/peer-practice/queue",
    response_model=schemas.QueueStatus,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.UnknownExamError, Unauthenticated, InvalidAudience, AudienceNotYours),
)
async def join_queue(
    body: schemas.JoinQueue, principal: CurrentPrincipal, session: Session
) -> schemas.QueueStatus:
    """Joining twice returns the place you already hold rather than a second one."""
    return await service.join_queue(
        session,
        user_id=principal.user_id,
        exam_code=body.exam_code,
        audience=body.audience.to_audience(),
    )


@router.get(
    "/peer-practice/queue/{entry_id}",
    response_model=schemas.QueueStatus,
    responses=error_responses(Unauthenticated, errors.QueueEntryNotFound),
)
async def read_status(
    entry_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.QueueStatus:
    """Position, how many are waiting, and the session if one has been made —
    one call, because the client polls this every few seconds."""
    return await service.read_status(session, entry_id, user_id=principal.user_id)


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
    """The streaming form of the route above it (ADR 0015).

    The place in the product where polling cost the most: somebody is sitting
    watching the screen, and the whole feature is how fast they get into a room
    with another person. Closes as soon as the answer stops being "waiting".
    """
    return StreamingResponse(
        service_stream.queue_stream(entry_id, principal.user_id, bus=bus, open_session=open_session),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


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


@router.get(
    "/me/practice-sessions",
    response_model=Page[schemas.PracticeSessionRead],
    responses=error_responses(Unauthenticated),
)
async def list_my_sessions(
    principal: CurrentPrincipal, session: Session
) -> Page[schemas.PracticeSessionRead]:
    items = await service.list_my_sessions(session, principal.user_id)
    return Page(items=items, next_cursor=None)


@router.get(
    "/me/practice-sessions/{session_id}",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def read_session(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.PracticeSessionRead:
    return await service.read_session(session, session_id, user_id=principal.user_id)


@router.post(
    "/me/practice-sessions/{session_id}/end",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(Unauthenticated, errors.SessionNotFound, errors.SessionAlreadyEnded),
)
async def end_session(
    session_id: uuid.UUID,
    body: schemas.EndSession,
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
) -> schemas.PracticeSessionRead:
    return await service.end_session(
        session, session_id, user_id=principal.user_id, reason=body.reason, now=clock.now()
    )


@router.post(
    "/me/practice-sessions/{session_id}/voice-token",
    response_model=schemas.RoomGrant,
    responses=error_responses(
        Unauthenticated,
        errors.SessionNotFound,
        errors.SessionAlreadyEnded,
        errors.VoiceUnavailable,
    ),
)
async def voice_token(
    session_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Annotated[VoiceTokens, Depends(service.get_voice_tokens)],
) -> schemas.RoomGrant:
    """A way into the room the pair were matched into.

    `practice_sessions.room_name` has been written since the slice landed and
    nothing could mint a token for it, so two people could be paired and then
    had nowhere to meet.
    """
    return await service.voice_grant(
        session, session_id, user_id=principal.user_id, tokens=tokens, settings=settings
    )
