from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Unauthenticated, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.features.entitlements import schemas, service

router = APIRouter(tags=["entitlements"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/me/entitlements",
    response_model=Page[schemas.EntitlementRead],
    responses=error_responses(Unauthenticated),
)
async def list_my_entitlements(
    principal: CurrentPrincipal, session: Session, clock: ClockDep
) -> Page[schemas.EntitlementRead]:
    """Expired grants are included with `live` computed, because "your access
    ended on the 3rd" is a more useful answer than an empty list."""
    items = await service.list_for_user(session, principal.user_id, now=clock.now())
    return Page(items=items, next_cursor=None)
