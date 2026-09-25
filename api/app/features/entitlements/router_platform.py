"""The platform console's view of entitlements. Every route is `PlatformAdmin`.

Kept apart from `router.py`, where a person reads their own grants and an
institution manages the ones it made: these cross every tenant, and a file
named for that is the answer to "who can call this?".
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
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
    """Every grant this person has held — purchase, institution, trial, admin — with `live`
    computed now and revoked ones kept."""
    _ = admin
    items = await service_platform.list_for_user(session, user_id, now=clock.now())
    return Page(items=items, next_cursor=None)


@router.post(
    "/platform/users/{user_id}/entitlements",
    response_model=schemas.PlatformEntitlementRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.GranteeNotFound, errors.UnknownExamError),
)
async def grant_entitlement_for_support(
    user_id: uuid.UUID,
    body: schemas.PlatformGrantEntitlement,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformEntitlementRead:
    """Grant access outright, source `admin`, with the reason in the audit log. Not for a
    purchase that failed to apply: replay that instead."""
    return await service_platform.grant(
        session,
        user_id,
        exam_code=body.exam_code,
        ends_at=body.ends_at,
        note=body.note,
        actor=admin,
        now=clock.now(),
    )


@router.patch(
    "/platform/entitlements/{entitlement_id}",
    response_model=schemas.PlatformEntitlementRead,
    responses=error_responses(Forbidden, errors.EntitlementNotFound),
)
async def extend_entitlement_for_support(
    entitlement_id: uuid.UUID,
    body: schemas.ExtendEntitlement,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformEntitlementRead:
    """Move the end date. A renewal is this rather than a second row."""
    return await service_platform.extend(
        session, entitlement_id, ends_at=body.ends_at, note=body.note, actor=admin, now=clock.now()
    )


@router.post(
    "/platform/entitlements/{entitlement_id}/revoke",
    response_model=schemas.PlatformEntitlementRead,
    responses=error_responses(Forbidden, errors.EntitlementNotFound),
)
async def revoke_entitlement_for_support(
    entitlement_id: uuid.UUID,
    body: schemas.RevokeEntitlement,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.PlatformEntitlementRead:
    """Withdraw a grant; the row stays so the history holds."""
    return await service_platform.revoke(
        session, entitlement_id, reason=body.reason, actor=admin, now=clock.now()
    )
