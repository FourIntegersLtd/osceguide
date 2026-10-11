"""The platform-admin route over community posts: the moderation queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.tenancy import PlatformAdmin
from app.features.community import schemas, service

router = APIRouter(tags=["community"])


@router.get(
    "/platform/moderation/posts",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Forbidden),
)
async def list_moderation_posts(
    admin: PlatformAdmin,
    principal: CurrentPrincipal,
    session: Session,
    params: Annotated[CursorParams, Depends()],
    days: Annotated[int, Query(ge=1, le=30)] = 7,
) -> Page[schemas.PostRead]:
    """Recent community and station posts for platform moderators."""
    _ = admin
    return await service.list_moderation_queue(session, viewer_id=principal.user_id, params=params, days=days)
