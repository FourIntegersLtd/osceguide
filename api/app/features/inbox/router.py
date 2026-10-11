"""HTTP routes for a person's inbox and for staff writing to it."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, InvalidInput, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.rate_limit import USER_WRITE, TooManyRequests, per_user
from app.core.tenancy import PlatformAdmin
from app.features.inbox import errors, schemas, service

router = APIRouter(tags=["inbox"])


@router.get(
    "/me/messages",
    response_model=Page[schemas.InboxMessageRead],
    responses=error_responses(Unauthenticated, InvalidInput),
)
async def list_my_messages(
    principal: CurrentPrincipal, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.InboxMessageRead]:
    """My messages and the announcements posted since I joined, newest first."""
    return await service.my_messages(session, user_id=principal.user_id, params=page)


@router.get(
    "/me/messages/unread-count",
    response_model=schemas.InboxUnreadCount,
    responses=error_responses(Unauthenticated),
)
async def read_unread_count(principal: CurrentPrincipal, session: Session) -> schemas.InboxUnreadCount:
    """The number on the inbox badge."""
    return await service.unread_count(session, user_id=principal.user_id)


@router.post(
    "/me/messages/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(per_user(USER_WRITE))],
    responses=error_responses(Unauthenticated, TooManyRequests),
)
async def read_all_messages(principal: CurrentPrincipal, session: Session) -> Response:
    """Mark everything in my inbox as read."""
    await service.mark_all_read(session, user_id=principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/me/messages/{message_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(per_user(USER_WRITE))],
    responses=error_responses(Unauthenticated, errors.InboxMessageNotFound, TooManyRequests),
)
async def read_message(message_id: uuid.UUID, principal: CurrentPrincipal, session: Session) -> Response:
    """Mark one message as read."""
    await service.mark_read(session, user_id=principal.user_id, message_id=message_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/platform/users/{user_id}/messages",
    response_model=schemas.SentInboxMessage,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, Forbidden, errors.UserNotFound),
)
async def send_user_note(
    user_id: uuid.UUID, body: schemas.SendUserNote, admin: PlatformAdmin, session: Session
) -> schemas.SentInboxMessage:
    """A note to one person's inbox. In-app only; no email is sent."""
    return await service.send_note(session, actor=admin, user_id=user_id, body=body)


@router.get(
    "/platform/announcements",
    response_model=Page[schemas.PlatformAnnouncementRead],
    responses=error_responses(Unauthenticated, Forbidden, InvalidInput),
)
async def list_announcements(
    _admin: PlatformAdmin, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.PlatformAnnouncementRead]:
    """Every announcement, withdrawn ones included, with how many people read it."""
    return await service.list_announcements(session, params=page)


@router.post(
    "/platform/announcements",
    response_model=schemas.SentInboxMessage,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Unauthenticated, Forbidden),
)
async def post_announcement(
    body: schemas.PostAnnouncement, admin: PlatformAdmin, session: Session
) -> schemas.SentInboxMessage:
    """Tell every learner something. Reaches accounts that exist now; later sign-ups do not see it."""
    return await service.post_announcement(session, actor=admin, body=body)


@router.post(
    "/platform/announcements/{message_id}/withdraw",
    response_model=schemas.PlatformAnnouncementRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.AnnouncementNotFound),
)
async def withdraw_announcement(
    message_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.PlatformAnnouncementRead:
    """Hide an announcement from every inbox."""
    return await service.withdraw_announcement(session, actor=admin, message_id=message_id, at=clock.now())
