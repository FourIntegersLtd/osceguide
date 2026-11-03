"""The practice sessions a learner has been matched into.

`router.py` keeps the queue half; these routes read and drive a session that
already exists, and the pair inside it.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.db import SessionOpenerDep
from app.core.errors import Unauthenticated, error_responses
from app.core.events import get_event_bus
from app.core.logging import get_logger
from app.core.openapi import sse_responses
from app.core.pagination import Page
from app.core.ports import ClockDep, EventBus, VoiceTokens
from app.core.rate_limit import OUTBOUND_EMAIL, USER_WRITE, TooManyRequests, per_user
from app.core.settings import SettingsDep
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.streams import StreamPrincipal
from app.features.peer_practice import (
    errors,
    schemas,
    service,
    service_match,
    service_reports,
    service_stream,
    service_voice,
)

log = get_logger(__name__)
router = APIRouter(tags=["peer-practice"])


# Every practice session this caller has been matched into, as doctor or patient.
@router.get(
    "/me/practice-sessions",
    response_model=Page[schemas.PracticeSessionRead],
    responses=error_responses(Unauthenticated),
)
async def list_my_sessions(
    principal: CurrentPrincipal, session: Session
) -> Page[schemas.PracticeSessionRead]:
    sessions = await service.list_my_sessions(session, principal.user_id)
    return Page(items=sessions, next_cursor=None)


# One practice session this caller is part of.
@router.get(
    "/me/practice-sessions/{session_id}",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(Unauthenticated, errors.SessionNotFound),
)
async def read_session(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PracticeSessionRead:
    return await service.read_session(session, session_id, user_id=principal.user_id, now=clock.now())


# Mark this caller as present, driving the session's phase forward if it is due.
@router.post(
    "/me/practice-sessions/{session_id}/presence",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(
        Unauthenticated, errors.SessionNotFound, errors.SessionAlreadyEnded, errors.NotYetAcceptedError
    ),
)
async def record_presence(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PracticeSessionRead:
    return await service.touch_presence(session, session_id, user_id=principal.user_id, now=clock.now())


# Accept a pending match. The pair is joinable once both sides have.
@router.post(
    "/me/practice-sessions/{session_id}/accept",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(
        Unauthenticated, errors.SessionNotFound, errors.PartnerUnavailableError, errors.NotEntitled
    ),
)
async def accept_match(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PracticeSessionRead:
    return await service_match.accept_match(session, session_id, user_id=principal.user_id, now=clock.now())


# Decline a pending match, ending it and requeuing a partner who had already accepted.
@router.post(
    "/me/practice-sessions/{session_id}/decline",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(
        Unauthenticated, errors.SessionNotFound, errors.PartnerUnavailableError, errors.SessionAlreadyEnded
    ),
)
async def decline_match(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PracticeSessionRead:
    return await service_match.decline_match(session, session_id, user_id=principal.user_id, now=clock.now())


# Pushes this session's phase and presence until it ends.
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
        service_stream.session_stream(session_id, principal.user_id, bus=bus, open_session=open_session),
        media_type=MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


# One participant's rating and comment on a session they were part of.
@router.post(
    "/me/practice-sessions/{session_id}/feedback",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(
        TooManyRequests, Unauthenticated, errors.SessionNotFound, errors.FeedbackNotOpenError
    ),
    dependencies=[Depends(per_user(USER_WRITE))],
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


# Flag the other participant's conduct in a session, emailed to support.
@router.post(
    "/me/practice-sessions/{session_id}/report-abuse",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(TooManyRequests, Unauthenticated, errors.SessionNotFound),
    dependencies=[Depends(per_user(OUTBOUND_EMAIL))],
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


# Flag that the other participant never turned up, emailed to support.
@router.post(
    "/me/practice-sessions/{session_id}/report-no-show",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(TooManyRequests, Unauthenticated, errors.SessionNotFound),
    dependencies=[Depends(per_user(OUTBOUND_EMAIL))],
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


# End a session early, recording why.
@router.post(
    "/me/practice-sessions/{session_id}/end",
    response_model=schemas.PracticeSessionRead,
    responses=error_responses(
        Unauthenticated, errors.SessionNotFound, errors.SessionAlreadyEnded, errors.NotYetAcceptedError
    ),
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
        Unauthenticated,
        errors.SessionNotFound,
        errors.SessionAlreadyEnded,
        errors.NotYetAcceptedError,
        errors.VoiceUnavailable,
        errors.NotEntitled,
    ),
)
async def voice_token(
    session_id: uuid.UUID,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
    tokens: Annotated[VoiceTokens, Depends(service_voice.get_voice_tokens)],
) -> schemas.RoomGrant:
    """A way into the room the pair were matched into."""
    return await service_voice.voice_grant(
        session,
        session_id,
        user_id=principal.user_id,
        tokens=tokens,
        settings=settings,
        now=clock.now(),
    )
