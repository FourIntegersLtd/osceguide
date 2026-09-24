"""The practice sessions a learner has been matched into.

Split from `router.py`, which keeps the queue half: these routes read and
drive a session that already exists, and the pair inside it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import SessionOpenerDep, get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.events import get_event_bus
from app.core.logging import get_logger
from app.core.openapi import sse_responses
from app.core.pagination import Page
from app.core.ports import ClockDep, EventBus, VoiceTokens
from app.core.settings import SettingsDep
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.features.peer_practice import (
    errors,
    schemas,
    service,
    service_reports,
    service_stream_session,
    service_voice,
)

log = get_logger(__name__)
router = APIRouter(tags=["peer-practice"])
Session = Annotated[AsyncSession, Depends(get_session)]


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
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PracticeSessionRead:
    return await service.read_session(session, session_id, user_id=principal.user_id, now=clock.now())


@router.post(
    "/me/practice-sessions/{session_id}/presence",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(Unauthenticated, errors.SessionNotFound, errors.SessionAlreadyEnded),
)
async def record_presence(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PracticeSessionRead:
    return await service.touch_presence(session, session_id, user_id=principal.user_id, now=clock.now())


@router.get(
    "/me/practice-sessions/{session_id}/stream",
    responses=sse_responses(schemas.PracticeSessionRead, Unauthenticated, errors.SessionNotFound),
    response_class=StreamingResponse,
)
async def stream_session(
    session_id: uuid.UUID,
    principal: StreamPrincipal,
    bus: Annotated[EventBus, Depends(get_event_bus)],
    open_session: SessionOpenerDep,
) -> StreamingResponse:
    return StreamingResponse(
        service_stream_session.session_stream(
            session_id, principal.user_id, bus=bus, open_session=open_session
        ),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


@router.post(
    "/me/practice-sessions/{session_id}/feedback",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def session_feedback(
    session_id: uuid.UUID,
    body: schemas.SessionFeedback,
    principal: CurrentPrincipal,
    session: Session,
) -> schemas.PracticeSessionRead:
    return await service.submit_feedback(
        session,
        session_id,
        user_id=principal.user_id,
        rating=body.rating,
        comment=body.comment,
        would_practice_again=body.would_practice_again,
    )


@router.post(
    "/me/practice-sessions/{session_id}/report-abuse",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def report_abuse(
    session_id: uuid.UUID,
    body: schemas.ReportAbuse,
    principal: CurrentPrincipal,
    session: Session,
) -> Response:
    log.warning(
        "practice session abuse report",
        session_id=str(session_id),
        reporter=str(principal.user_id),
        message=body.message,
    )
    await service_reports.report_abuse(
        session, session_id, reporter_id=principal.user_id, message=body.message
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/me/practice-sessions/{session_id}/report-no-show",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def report_no_show(
    session_id: uuid.UUID,
    body: schemas.ReportNoShow,
    principal: CurrentPrincipal,
    session: Session,
) -> Response:
    log.info(
        "practice session no-show report",
        session_id=str(session_id),
        reporter=str(principal.user_id),
        message=body.message or "",
    )
    await service_reports.report_no_show(
        session, session_id, reporter_id=principal.user_id, message=body.message
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        session,
        session_id,
        user_id=principal.user_id,
        reason=body.reason,
        now=clock.now(),
    )


@router.post(
    "/me/practice-sessions/{session_id}/voice-token",
    response_model=schemas.RoomGrant,
    responses=error_responses(
        Unauthenticated, errors.SessionNotFound, errors.SessionAlreadyEnded, errors.VoiceUnavailable
    ),
)
async def voice_token(
    session_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    tokens: Annotated[VoiceTokens, Depends(service_voice.get_voice_tokens)],
) -> schemas.RoomGrant:
    """A way into the room the pair were matched into."""
    return await service_voice.voice_grant(
        session,
        session_id,
        user_id=principal.user_id,
        tokens=tokens,
        settings=settings,
    )
