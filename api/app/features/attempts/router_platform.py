"""The platform console's view of attempts. Every route is `PlatformAdmin`.

The candidate-facing reads in `router.py` already admit a platform admin by
id. What they cannot do is find an attempt from a person, or say why it has no
feedback; that is what these are for.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import PlatformAdmin
from app.features.attempts import errors, schemas_platform, service_platform

router = APIRouter(tags=["attempts"])

Session = Annotated[AsyncSession, Depends(get_session)]

STATUS_PATTERN = "^(created|running|interaction_complete|evaluated|failed)$"


@router.get(
    "/platform/users/{user_id}/attempts",
    response_model=Page[schemas_platform.PlatformAttemptRead],
    responses=error_responses(Forbidden, errors.UserNotFound),
)
async def list_user_attempts_for_support(
    user_id: uuid.UUID,
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    status: Annotated[
        str | None, Query(pattern=STATUS_PATTERN, description="Only attempts in this state")
    ] = None,
) -> Page[schemas_platform.PlatformAttemptRead]:
    """One person's attempts, newest first, each saying whether its transcript
    arrived, whether it was marked, and what the queue holds for it."""
    _ = admin
    items, next_cursor = await service_platform.list_for_user(
        session, user_id, limit=page.limit, cursor=page.cursor, status=status
    )
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/platform/attempts/{attempt_id}",
    response_model=schemas_platform.PlatformAttemptDetail,
    responses=error_responses(Forbidden, errors.AttemptNotFound),
)
async def read_attempt_for_support(
    attempt_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas_platform.PlatformAttemptDetail:
    """Everything support needs about one attempt: the frozen definition's
    presence, how many turns arrived, and every marking job ever queued."""
    _ = admin
    return await service_platform.read_detail(session, attempt_id)
