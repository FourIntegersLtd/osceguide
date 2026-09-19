"""The platform console's view of entitlements. Every route is `PlatformAdmin`.

Kept apart from `router.py`, where a person reads their own grants and an
institution manages the ones it made: these cross every tenant, and a file
named for that is the answer to "who can call this?".
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.entitlements import errors, schemas, service_platform

router = APIRouter(tags=["entitlements"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/platform/users/{user_id}/entitlements",
    response_model=Page[schemas.PlatformEntitlementRead],
    responses=error_responses(Forbidden, errors.GranteeNotFound),
)
async def list_user_entitlements_for_support(
    user_id: uuid.UUID, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> Page[schemas.PlatformEntitlementRead]:
    """Every grant this person has held — purchase, institution, trial, admin —
    with `live` computed now and revoked ones kept, because "your access ended
    on the 3rd" is the answer support is usually looking for."""
    _ = admin
    items = await service_platform.list_for_user(session, user_id, now=clock.now())
    return Page(items=items, next_cursor=None)
