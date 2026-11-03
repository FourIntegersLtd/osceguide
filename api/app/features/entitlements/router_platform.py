"""The platform console's view of entitlements. Every route is `PlatformAdmin`.

Kept apart from `router.py`, where a person reads their own grants and an
institution manages the ones it made: these cross every tenant, and a file
named for that is the answer to "who can call this?".
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.ports import ClockDep
from app.core.tenancy import PlatformAdmin
from app.features.entitlements import errors, schemas, service_platform

router = APIRouter(tags=["entitlements"])


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
