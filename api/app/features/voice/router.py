"""Browser-facing voice routes: a token to join an attempt's station room, or a place in line for one."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import SessionOpenerDep, get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.events import get_event_bus
from app.core.openapi import sse_responses
from app.core.ports import EventBus, VoiceTokens
from app.core.settings import SettingsDep
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.features.voice import errors, schemas, service

router = APIRouter(tags=["voice"])

Session = Annotated[AsyncSession, Depends(get_session)]


# Issue a LiveKit token for this attempt's station room, or a place in line when every seat is taken.
@router.post(
    "/attempts/{attempt_id}/voice-token",
    response_model=schemas.VoiceGrant,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": schemas.VoiceQueueStanding,
            "description": "Every seat is taken: the candidate is in line. Watch `voice-queue`, then retry.",
        },
        **error_responses(
            Unauthenticated,
            errors.AttemptNotFound,
            errors.AttemptNotYours,
            errors.AttemptNotJoinable,
            errors.VoiceUnavailable,
        ),
    },
)
async def issue_voice_token(
    attempt_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Annotated[VoiceTokens, Depends(service.get_voice_tokens)],
) -> schemas.VoiceGrant | JSONResponse:
    grant = await service.grant_for_attempt(
        session,
        attempt_id,
        requester_id=principal.user_id,
        tokens=tokens,
        settings=settings,
    )
    if isinstance(grant, schemas.VoiceQueueStanding):
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=grant.model_dump())
    return grant


# Push this attempt's place in line until a seat is free for it.
@router.get(
    "/attempts/{attempt_id}/voice-queue",
    responses=sse_responses(
        schemas.VoiceQueueStanding, Unauthenticated, errors.AttemptNotFound, errors.AttemptNotYours
    ),
    response_class=StreamingResponse,
)
async def stream_voice_queue(
    attempt_id: uuid.UUID,
    principal: StreamPrincipal,
    settings: SettingsDep,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
) -> StreamingResponse:
    room = await service.ensure_queue_watchable(
        attempt_id, requester_id=principal.user_id, open_session=open_session
    )
    return StreamingResponse(
        service.queue_stream(room, settings=settings, bus=bus),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


# Step out of line, so everybody behind this attempt moves up at once.
@router.delete(
    "/attempts/{attempt_id}/voice-queue",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(
        Unauthenticated,
        errors.AttemptNotFound,
        errors.AttemptNotYours,
        errors.VoiceUnavailable,
    ),
)
async def leave_voice_queue(
    attempt_id: uuid.UUID,
    principal: CurrentPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
) -> Response:
    room = await service.ensure_queue_watchable(
        attempt_id, requester_id=principal.user_id, open_session=open_session
    )
    await service.leave_queue(room, bus=bus)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
