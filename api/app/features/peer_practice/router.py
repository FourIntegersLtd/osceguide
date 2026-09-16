from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.features.peer_practice import errors, schemas, service

router = APIRouter(tags=["peer-practice"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/peer-practice/queue",
    response_model=schemas.QueueStatus,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated),
)
async def join_queue(
    body: schemas.JoinQueue, principal: CurrentPrincipal, session: Session
) -> schemas.QueueStatus:
    """Joining twice returns the place you already hold rather than a second one."""
    return await service.join_queue(session, user_id=principal.user_id, exam_code=body.exam_code)


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
