from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin
from app.features.entitlements import errors, schemas, service, service_org

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
    entitlements = await service.list_for_user(session, principal.user_id, now=clock.now())
    return Page(items=entitlements, next_cursor=None)


@router.get(
    "/orgs/{org_slug}/entitlements",
    response_model=Page[schemas.EntitlementRead],
    responses=error_responses(Forbidden),
)
async def list_org_entitlements(
    workspace: OrgAdmin, session: Session, clock: ClockDep
) -> Page[schemas.EntitlementRead]:
    """What this institution has granted, revoked ones included."""
    entitlements = await service_org.list_for_org(session, workspace.org_id, now=clock.now())
    return Page(items=entitlements, next_cursor=None)


@router.post(
    "/orgs/{org_slug}/entitlements",
    response_model=schemas.EntitlementRead,
    status_code=201,
    responses=error_responses(Forbidden, errors.GranteeNotFound, errors.UnknownExamError),
)
async def grant_org_entitlement(
    body: schemas.GrantEntitlement, workspace: OrgAdmin, session: Session
) -> schemas.EntitlementRead:
    """Grant one of this institution's people access to an exam it runs, for practising between
    sittings. A trainee's exam-day slot never needs this: a dispatched slot skips the gate."""
    return await service_org.grant_for_org(
        session,
        workspace.org_id,
        email=body.email,
        exam_code=body.exam_code,
        ends_at=body.ends_at,
        actor=workspace.principal,
    )


@router.post(
    "/orgs/{org_slug}/entitlements/{entitlement_id}/revoke",
    response_model=schemas.EntitlementRead,
    responses=error_responses(Forbidden, errors.EntitlementNotFound),
)
async def revoke_org_entitlement(
    entitlement_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.EntitlementRead:
    return await service_org.revoke_for_org(session, workspace.org_id, entitlement_id, now=clock.now())
