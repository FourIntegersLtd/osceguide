from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import MaybePrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.ports import ClockDep
from app.core.rate_limit import Limit, TooManyRequests, caller_key, check
from app.core.tenancy import PlatformAdmin
from app.features.public_site import errors, schemas, service

router = APIRouter(tags=["public-site"])

Session = Annotated[AsyncSession, Depends(get_session)]

# A form anybody on the internet can post to. Sized for a person who sends one
# message, changes their mind and sends a better one — not for a script.
SEND_MESSAGE = Limit(name="site-message", allowance=5, window_seconds=600)

# Generous, because a landing page is meant to be hit. It is here at all
# because a cold cache makes this four aggregate queries, and a burst of misses
# would run all four for every caller in it.
READ_STATISTICS = Limit(name="site-statistics", allowance=60, window_seconds=60)


@router.get(
    "/site/statistics",
    response_model=schemas.SiteStatistics,
    responses=error_responses(TooManyRequests),
)
async def read_statistics(request: Request, session: Session, clock: ClockDep) -> schemas.SiteStatistics:
    """The counters on the landing page's numbers band.

    Unauthenticated, because the landing page is what a visitor sees before anything else. Cached for
    ten minutes: the busiest page on the site should not cost four aggregate queries per view, and no
    figure here changes meaningfully in that time.
    """
    await check(READ_STATISTICS, caller_key(request))
    return await service.statistics(session, now=clock.now())


@router.post(
    "/site/messages",
    response_model=schemas.MessageAccepted,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(errors.InvalidMessageError, TooManyRequests),
)
async def send_message(
    request: Request,
    body: schemas.SendMessage,
    principal: MaybePrincipal,
    session: Session,
) -> schemas.MessageAccepted:
    """The contact form, and the product-feedback box inside the product.

    Signed in or not: the contact form is on the public site and the feedback
    box is on a screen somebody is already using. When there is a token the
    message is filed against them, which is how a reply finds the right person
    without asking them to type their address again.
    """
    await check(SEND_MESSAGE, caller_key(request))
    return await service.send(session, body, user_id=principal.user_id if principal else None)


@router.get(
    "/platform/site/messages",
    response_model=list[schemas.MessageRead],
    responses=error_responses(Unauthenticated, Forbidden),
)
async def list_messages(
    _admin: PlatformAdmin,
    session: Session,
    kind: Annotated[str | None, Query(description="contact or product_feedback")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[schemas.MessageRead]:
    """The inbox. Platform admin, because it is everybody's messages."""
    return await service.list_messages(session, kind=kind, limit=limit)


@router.post(
    "/platform/site/messages/{message_id}/handled",
    response_model=schemas.MessageRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.MessageNotFound),
)
async def mark_handled(
    message_id: uuid.UUID,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.MessageRead:
    """Answered, or read and nothing to do. Either way it leaves the queue."""
    return await service.mark_handled(session, message_id=message_id, by=admin.user_id, at=clock.now())
