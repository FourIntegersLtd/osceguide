"""Routes for exam access: a person's own grants, and an org admin granting or revoking them for trainees."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgAdmin
from app.features.entitlements import errors, schemas, service, service_org, service_practice_access

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
    workspace: OrgAdmin,
    session: Session,
    clock: ClockDep,
    page: Annotated[CursorParams, Depends()],
    search: Annotated[str | None, Query(description="A grantee's name, email, or the exam's code")] = None,
) -> Page[schemas.EntitlementRead]:
    """A page of what this institution has granted, revoked ones included."""
    entitlements, next_cursor = await service_org.list_for_org(
        session, workspace.org_id, now=clock.now(), limit=page.limit, cursor=page.cursor, search=search
    )
    return Page(items=entitlements, next_cursor=next_cursor)


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


# Revoke an access grant an organisation gave to one of its people.
@router.post(
    "/orgs/{org_slug}/entitlements/{entitlement_id}/revoke",
    response_model=schemas.EntitlementRead,
    responses=error_responses(Forbidden, errors.EntitlementNotFound),
)
async def revoke_org_entitlement(
    entitlement_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.EntitlementRead:
    return await service_org.revoke_for_org(session, workspace.org_id, entitlement_id, now=clock.now())


# Everyone this organisation has given practice access, invited and revoked included.
@router.get(
    "/orgs/{org_slug}/practice-access",
    response_model=schemas.PracticeAccessList,
    responses=error_responses(Forbidden),
)
async def list_practice_access(
    workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.PracticeAccessList:
    items = await service_practice_access.list_practice_access(session, workspace.org_id, now=clock.now())
    return schemas.PracticeAccessList(items=items)


@router.post(
    "/orgs/{org_slug}/practice-access",
    response_model=schemas.PracticeAccessItem,
    status_code=201,
    responses=error_responses(
        Forbidden, errors.InvalidPracticeEmail, errors.UnknownExamError, errors.PracticeAccessExists
    ),
)
async def grant_practice_access(
    body: schemas.GrantPracticeAccess, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.PracticeAccessItem:
    """Give one person practice access to an exam this organisation offers.

    An address with no account is invited: the account is created without a password and
    the grant is attached to it, usable once they choose a password from the email.
    """
    item = await service_practice_access.grant_practice_access(
        session,
        workspace.org_id,
        email=body.email,
        exam_id=body.exam_id,
        actor=workspace.principal,
        now=clock.now(),
    )
    return schemas.PracticeAccessItem(item=item)


@router.post(
    "/orgs/{org_slug}/practice-access/bulk",
    response_model=schemas.BulkPracticeAccessResults,
    responses=error_responses(Forbidden),
)
async def grant_practice_access_in_bulk(
    body: schemas.BulkGrantPracticeAccess, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkPracticeAccessResults:
    """Up to 500 rows the client parsed from a CSV; each row reports its own outcome."""
    results = await service_practice_access.grant_practice_access_in_bulk(
        session, workspace.org_id, rows=body.rows, actor=workspace.principal, now=clock.now()
    )
    return schemas.BulkPracticeAccessResults(results=results)


# Withdraw one practice-access grant; the row stays on record.
@router.post(
    "/orgs/{org_slug}/practice-access/{access_id}/revoke",
    response_model=schemas.PracticeAccessItem,
    responses=error_responses(Forbidden, errors.EntitlementNotFound),
)
async def revoke_practice_access(
    access_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.PracticeAccessItem:
    item = await service_practice_access.revoke_practice_access(
        session, workspace.org_id, access_id, actor=workspace.principal, now=clock.now()
    )
    return schemas.PracticeAccessItem(item=item)
