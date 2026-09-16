from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.features.community import errors, schemas, service

router = APIRouter(tags=["community"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/community/questions",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated),
)
async def list_questions(
    principal: CurrentPrincipal, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.PostRead]:
    items, next_cursor = await service.list_questions(
        session, viewer_id=principal.user_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/community/questions",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, errors.EmptyContentError),
)
async def ask(
    body: schemas.CreateQuestion, principal: CurrentPrincipal, session: Session
) -> schemas.PostRead:
    return await service.ask(
        session,
        author_id=principal.user_id,
        title=body.title,
        body=body.body,
        exam_code=body.exam_code,
    )


@router.get(
    "/community/questions/{question_id}/replies",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated, errors.PostNotFound),
)
async def list_replies(
    question_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> Page[schemas.PostRead]:
    items = await service.list_replies(session, question_id, viewer_id=principal.user_id)
    return Page(items=items, next_cursor=None)


@router.post(
    "/community/questions/{question_id}/replies",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, errors.PostNotFound, errors.EmptyContentError),
)
async def reply(
    question_id: uuid.UUID,
    body: schemas.CreateReply,
    principal: CurrentPrincipal,
    session: Session,
) -> schemas.PostRead:
    return await service.reply(session, question_id, author_id=principal.user_id, body=body.body)


@router.post(
    "/community/posts/{post_id}/like",
    response_model=schemas.PostRead,
    responses=error_responses(Unauthenticated, errors.PostNotFound),
)
async def like(post_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> schemas.PostRead:
    """Idempotent. b2c increments a counter, so a double tap counts twice."""
    return await service.set_like(session, post_id, user_id=principal.user_id, liked=True)


@router.delete(
    "/community/posts/{post_id}/like",
    response_model=schemas.PostRead,
    responses=error_responses(Unauthenticated, errors.PostNotFound),
)
async def unlike(post_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> schemas.PostRead:
    return await service.set_like(session, post_id, user_id=principal.user_id, liked=False)


@router.delete(
    "/community/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.PostNotFound, errors.NotYoursError),
)
async def remove(
    post_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> Response:
    """Your own, or anyone's if you are a platform admin.

    b2c's delete routes carry no decorator at all, so anyone can remove anyone's.
    """
    await service.remove(
        session,
        post_id,
        actor_id=principal.user_id,
        actor_is_admin=principal.is_platform_admin,
        now=clock.now(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/stations/{station_id}/comments",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated),
)
async def list_station_comments(
    station_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> Page[schemas.PostRead]:
    items = await service.list_station_comments(session, station_id, viewer_id=principal.user_id)
    return Page(items=items, next_cursor=None)


@router.post(
    "/stations/{station_id}/comments",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, errors.EmptyContentError),
)
async def comment_on_station(
    station_id: uuid.UUID,
    body: schemas.CreateStationComment,
    principal: CurrentPrincipal,
    session: Session,
) -> schemas.PostRead:
    return await service.comment_on_station(session, station_id, author_id=principal.user_id, body=body.body)
