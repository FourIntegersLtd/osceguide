from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import Page
from app.core.tenancy import PlatformAdmin
from app.features.community import schemas, service

router = APIRouter(tags=["community"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/platform/moderation/posts",
    response_model=Page[schemas.PostRead],
    responses=error_responses(Forbidden),
)
async def list_moderation_posts(
    admin: PlatformAdmin,
    principal: CurrentPrincipal,
    session: Session,
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> Page[schemas.PostRead]:
    """Recent community and station posts for platform moderators."""
    _ = admin
    items = await service.list_moderation_queue(session, viewer_id=principal.user_id, days=days, limit=limit)
    return Page(items=items, next_cursor=None)
