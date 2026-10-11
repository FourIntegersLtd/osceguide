"""HTTP routes for questions, replies, likes and station comments. Each hands straight to `service`."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import AudienceFilter, AudienceNotYours, InvalidAudience
from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.rate_limit import PUBLISH, USER_WRITE, TooManyRequests, per_user
from app.core.tenancy import admin_org_ids
from app.features.community import errors, schemas, service

router = APIRouter(tags=["community"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/community/questions",
    response_model=Page[schemas.PostRead],
    responses=error_responses(errors.UnknownExamError, Unauthenticated, errors.InvalidCategoryError),
)
async def list_questions(
    principal: CurrentPrincipal,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    room: Annotated[AudienceFilter, Depends()],
    mine: Annotated[bool, Query(description="Only the caller's own questions.")] = False,
    tag: Annotated[str | None, Query(description="Only questions carrying this tag.")] = None,
    exam_code: Annotated[str | None, Query(description="Only questions asked about this exam.")] = None,
    category: Annotated[
        str | None, Query(description="Only questions filed under general, platform, skills or exam.")
    ] = None,
) -> Page[schemas.PostRead]:
    """Everything this caller may see, or one room of it.

    Without a filter the answer spans the public pool and every institution and
    group the caller belongs to, which is what a single feed should be. `tag` and
    `exam_code` narrow that answer and can never widen it.
    """
    questions, next_cursor = await service.list_questions(
        session,
        viewer_id=principal.user_id,
        limit=page.limit,
        cursor=page.cursor,
        audience=room.audience,
        mine=mine,
        tag=tag,
        exam_code=exam_code,
        category=category,
    )
    return Page(items=questions, next_cursor=next_cursor)


@router.get(
    "/community/replies",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated, errors.InvalidAuthorFilter),
)
async def list_replies_by_author(
    principal: CurrentPrincipal,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    author: Annotated[str, Query(description="`me` — the caller's own answers.")] = "me",
) -> Page[schemas.PostRead]:
    """The answers this caller has written, across every question.

    `author` takes `me` and nothing else. Reading somebody else's answer
    history is a different question — "what has this person said" — and it is
    not what the tab asks, so the parameter refuses rather than quietly
    widening to any user id.
    """
    if author.strip().lower() != "me":
        raise errors.InvalidAuthorFilter()
    replies, next_cursor = await service.list_my_answers(
        session, viewer_id=principal.user_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=replies, next_cursor=next_cursor)


@router.get(
    "/community/questions/{question_id}",
    response_model=schemas.PostRead,
    responses=error_responses(Unauthenticated, errors.PostNotFound),
)
async def read_question(
    question_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> schemas.PostRead:
    """One question by id, so a deep link works whatever page the feed is on."""
    return await service.question_detail(session, question_id, viewer_id=principal.user_id)


# Ask a new question in the caller's chosen room, tagged for the feed filter.
@router.post(
    "/community/questions",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        TooManyRequests,
        errors.UnknownExamError,
        Unauthenticated,
        errors.EmptyContentError,
        errors.TagTooLongError,
        errors.TooManyTagsError,
        errors.InvalidCategoryError,
        errors.ExamRequiredError,
        InvalidAudience,
        AudienceNotYours,
    ),
    dependencies=[Depends(per_user(PUBLISH))],
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
        category=body.category,
        audience=body.audience.to_audience(),
        tags=body.tags,
    )


# Every reply under one question, oldest first.
@router.get(
    "/community/questions/{question_id}/replies",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated, errors.PostNotFound),
)
async def list_replies(
    question_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> Page[schemas.PostRead]:
    replies = await service.list_replies(session, question_id, viewer_id=principal.user_id)
    return Page(items=replies, next_cursor=None)


# Reply to a community question.
@router.post(
    "/community/questions/{question_id}/replies",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        TooManyRequests, Unauthenticated, errors.PostNotFound, errors.EmptyContentError
    ),
    dependencies=[Depends(per_user(PUBLISH))],
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
    responses=error_responses(TooManyRequests, Unauthenticated, errors.PostNotFound),
    dependencies=[Depends(per_user(USER_WRITE))],
)
async def like(post_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> schemas.PostRead:
    """Idempotent. b2c increments a counter, so a double tap counts twice."""
    return await service.set_like(session, post_id, user_id=principal.user_id, liked=True)


# Take back a like on a community post.
@router.delete(
    "/community/posts/{post_id}/like",
    response_model=schemas.PostRead,
    responses=error_responses(TooManyRequests, Unauthenticated, errors.PostNotFound),
    dependencies=[Depends(per_user(USER_WRITE))],
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
    """Your own, anyone's if you are a platform admin, or anything addressed
    inside an institution you administer.

    b2c's delete routes carry no decorator at all, so anyone can remove anyone's.
    """
    await service.remove(
        session,
        post_id,
        actor_id=principal.user_id,
        actor_is_admin=principal.is_platform_admin,
        moderates_org_ids=admin_org_ids(principal),
        now=clock.now(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Comments on one station that the caller may see.
@router.get(
    "/stations/{station_id}/comments",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated),
)
async def list_station_comments(
    station_id: uuid.UUID, principal: CurrentPrincipal, session: Session
) -> Page[schemas.PostRead]:
    comments = await service.list_station_comments(session, station_id, viewer_id=principal.user_id)
    return Page(items=comments, next_cursor=None)


# Leave a comment on a station, in the caller's chosen room.
@router.post(
    "/stations/{station_id}/comments",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        TooManyRequests,
        Unauthenticated,
        errors.StationNotFound,
        errors.EmptyContentError,
        InvalidAudience,
        AudienceNotYours,
    ),
    dependencies=[Depends(per_user(PUBLISH))],
)
async def comment_on_station(
    station_id: uuid.UUID,
    body: schemas.CreateStationComment,
    principal: CurrentPrincipal,
    session: Session,
) -> schemas.PostRead:
    return await service.comment_on_station(
        session,
        station_id,
        author_id=principal.user_id,
        body=body.body,
        audience=body.audience.to_audience(),
    )
