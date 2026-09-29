"""HTTP routes for offering, claiming and joining peer practice slots. Each hands straight to `service`."""

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
from app.features.marketplace import errors, schemas, service

router = APIRouter(tags=["marketplace"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/marketplace/slots",
    response_model=Page[schemas.PostRead],
    responses=error_responses(errors.UnknownExamError, Unauthenticated),
)
async def list_open_slots(
    principal: CurrentPrincipal,
    session: Session,
    clock: ClockDep,
    page: Annotated[CursorParams, Depends()],
    audience_filter: Annotated[AudienceFilter, Depends()],
    exam_code: Annotated[str | None, Query(max_length=32)] = None,
) -> Page[schemas.PostRead]:
    """Availability and claimed slots this caller can see — the public pool plus every institution and
    group they belong to."""
    posts, next_cursor = await service.list_open_slots(
        session,
        viewer_id=principal.user_id,
        now=clock.now(),
        limit=page.limit,
        cursor=page.cursor,
        audience=audience_filter.audience,
        exam_code=exam_code,
    )
    return Page(items=posts, next_cursor=next_cursor)


# Offer a new slot, addressed to the public, one institution or one teaching group.
@router.post(
    "/marketplace/slots",
    response_model=schemas.PostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        TooManyRequests,
        errors.UnknownExamError,
        errors.NotEntitled,
        Unauthenticated,
        InvalidAudience,
        AudienceNotYours,
    ),
    dependencies=[Depends(per_user(PUBLISH))],
)
async def offer_slot(
    body: schemas.CreatePost, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PostRead:
    return await service.offer_slot(
        session,
        owner_user_id=principal.user_id,
        exam_code=body.exam_code,
        now=clock.now(),
        starts_at=body.starts_at,
        duration_minutes=body.duration_minutes,
        note=body.note,
        audience=body.audience.to_audience(),
    )


@router.post(
    "/marketplace/slots/{post_id}/claim",
    response_model=schemas.PeerSessionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        TooManyRequests,
        Unauthenticated,
        errors.PostNotFound,
        errors.PostUnavailableError,
        errors.SlotAlreadyClaimedError,
        errors.CannotClaimOwnPostError,
        errors.NotEntitled,
    ),
    dependencies=[Depends(per_user(USER_WRITE))],
)
async def claim_slot(
    post_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PeerSessionRead:
    """Claimed once. The row is locked before it is examined, so the second of
    two simultaneous claims is told the slot is gone rather than double-booked."""
    return await service.claim_slot(session, post_id, claimer_user_id=principal.user_id, now=clock.now())


# Take back a slot you offered. Only the person who offered it may withdraw it.
@router.delete(
    "/marketplace/slots/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(
        Unauthenticated, errors.PostNotFound, errors.NotYoursError, errors.PostUnavailableError
    ),
)
async def withdraw_slot(
    post_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> Response:
    await service.withdraw_slot(session, post_id, actor_id=principal.user_id, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Every slot this caller has offered, including claimed and cancelled history.
@router.get(
    "/me/marketplace/posts",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Unauthenticated),
)
async def list_my_posts(principal: CurrentPrincipal, session: Session) -> Page[schemas.PostRead]:
    posts = await service.list_my_posts(session, viewer_id=principal.user_id)
    return Page(items=posts, next_cursor=None)


# Every session this caller has offered or claimed, latest start time first.
@router.get(
    "/me/peer-sessions",
    response_model=Page[schemas.PeerSessionRead],
    responses=error_responses(Unauthenticated),
)
async def list_my_sessions(
    principal: CurrentPrincipal,
    session: Session,
    page: Annotated[CursorParams, Depends()],
) -> Page[schemas.PeerSessionRead]:
    peer_sessions, next_cursor = await service.list_my_sessions(
        session, principal.user_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=peer_sessions, next_cursor=next_cursor)


@router.post(
    "/me/peer-sessions/{session_id}/join",
    response_model=schemas.PeerSessionRead,
    responses=error_responses(
        TooManyRequests,
        Unauthenticated,
        errors.SessionNotFound,
        errors.SessionNotOpen,
        errors.TooEarlyToJoinError,
    ),
    dependencies=[Depends(per_user(USER_WRITE))],
)
async def join_session(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> schemas.PeerSessionRead:
    return await service.join_session(session, session_id, user_id=principal.user_id, now=clock.now())


# Either person can call off a session that is still scheduled or under way.
@router.post(
    "/me/peer-sessions/{session_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(Unauthenticated, errors.SessionNotFound, errors.SessionNotOpen),
)
async def cancel_session(
    session_id: uuid.UUID, principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> Response:
    await service.cancel_peer_session(session, session_id, user_id=principal.user_id, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
