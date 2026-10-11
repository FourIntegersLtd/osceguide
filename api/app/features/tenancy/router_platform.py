"""The platform console's routes. Every one of them is `PlatformAdmin`.

A router of its own because the access rule is uniform and unlike the rest of
the API: these read across tenants rather than inside one, and keeping them in
a file named for that makes "who can call this?" a question answered by where
the route lives.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgReader, PlatformAdmin
from app.features.tenancy import errors, schemas, service, service_platform

router = APIRouter(tags=["tenancy"])


@router.get(
    "/platform/organizations",
    response_model=Page[schemas.OrganizationRead],
    responses=error_responses(Forbidden),
)
async def list_organizations(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    status: Annotated[str | None, Query(description="Filter by organisation status")] = None,
    search: Annotated[
        str | None, Query(max_length=200, description="Part of the organisation's name or slug")
    ] = None,
    org_type: Annotated[str | None, Query(description="Filter by organisation type")] = None,
) -> Page[schemas.OrganizationRead]:
    """Every organisation on the platform. The console's first screen."""
    organizations, next_cursor = await service_platform.list_organizations(
        session, limit=page.limit, cursor=page.cursor, status=status, search=search, org_type=org_type
    )
    return Page(items=organizations, next_cursor=next_cursor)


@router.patch(
    "/platform/organizations/{org_slug}",
    response_model=schemas.OrganizationRead,
    responses=error_responses(Forbidden, errors.OrgNotFound, errors.ContractDatesOutOfOrder),
)
async def update_organization(
    body: schemas.UpdateOrganization,
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.OrganizationRead:
    """Rename an organisation, change its type, record its contract dates, or require staff MFA."""
    return await service_platform.update_organization(
        session, workspace.org_id, changes=body, actor=admin, now=clock.now()
    )


@router.post(
    "/platform/organizations/{org_slug}/restore",
    response_model=schemas.OrganizationRead,
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def restore_organization(
    workspace: OrgReader, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.OrganizationRead:
    """Lift a suspension. Suspending had no inverse, and an action with none is
    one nobody dares use."""
    return await service_platform.restore_organization(
        session, org_id=workspace.org_id, actor=admin, now=clock.now()
    )


@router.get(
    "/platform/overview",
    response_model=schemas.PlatformOverview,
    responses=error_responses(Forbidden),
)
async def read_overview(admin: PlatformAdmin, session: Session, clock: ClockDep) -> schemas.PlatformOverview:
    """The numbers the console opens with, and the organisations to look at first."""
    _ = admin
    return await service_platform.overview(session, now=clock.now())


@router.post(
    "/platform/organizations/{org_slug}/contract",
    response_model=schemas.OrganizationRead,
    responses=error_responses(
        Forbidden, errors.OrgNotFound, errors.ContractDatesOutOfOrder, errors.ContractEndInPast
    ),
)
async def renew_contract(
    body: schemas.RenewContract,
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.OrganizationRead:
    """Record a renewal and lift the suspension it ends, in one step."""
    return await service_platform.renew_contract(
        session, workspace.org_id, terms=body, actor=admin, now=clock.now()
    )


# A page of one organisation's audit log, as seen by the platform console.
@router.get(
    "/platform/organizations/{org_slug}/audit",
    response_model=Page[schemas.AuditRead],
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def list_org_audit_for_support(
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
) -> Page[schemas.AuditRead]:
    _ = admin
    audit_entries, next_cursor = await service.list_audit(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=audit_entries, next_cursor=next_cursor)


@router.get(
    "/platform/audit",
    response_model=Page[schemas.PlatformAuditRead],
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def list_platform_audit(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    org_slug: Annotated[str | None, Query(description="Only one organisation's rows")] = None,
    actor_email: Annotated[str | None, Query(description="Only what this person did")] = None,
    action: Annotated[
        str | None, Query(description="An action name, or its prefix such as `entitlement.`")
    ] = None,
) -> Page[schemas.PlatformAuditRead]:
    """Who changed what, across every organisation and the platform itself."""
    _ = admin
    audit_entries, next_cursor = await service_platform.list_audit(
        session,
        org_slug=org_slug,
        actor_email=actor_email,
        action=action,
        limit=page.limit,
        cursor=page.cursor,
    )
    return Page(items=audit_entries, next_cursor=next_cursor)
