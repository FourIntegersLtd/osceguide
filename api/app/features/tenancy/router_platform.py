"""The platform console's routes. Every one of them is `PlatformAdmin`.

A router of its own because the access rule is uniform and unlike the rest of
the API: these read across tenants rather than inside one, and keeping them in
a file named for that makes "who can call this?" a question answered by where
the route lives.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgReader, PlatformAdmin
from app.features.tenancy import errors, schemas, service, service_memberships, service_platform

router = APIRouter(tags=["tenancy"])

Session = Annotated[AsyncSession, Depends(get_session)]


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
) -> Page[schemas.OrganizationRead]:
    """Every organisation on the platform. The console's first screen."""
    items, next_cursor = await service_platform.list_organizations(
        session, limit=page.limit, cursor=page.cursor, status=status
    )
    return Page(items=items, next_cursor=next_cursor)


@router.patch(
    "/platform/organizations/{org_slug}",
    response_model=schemas.OrganizationRead,
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def update_organization(
    body: schemas.UpdateOrganization,
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.OrganizationRead:
    """Rename an organisation, change its type, or record its contract dates."""
    return await service_platform.update_organization(session, workspace.org_id, changes=body, actor=admin)


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


@router.post(
    "/platform/organizations/{org_slug}/memberships",
    response_model=schemas.MembershipRead,
    status_code=201,
    responses=error_responses(Forbidden, errors.OrgNotFound, errors.MembershipExists),
)
async def seat_membership(
    body: schemas.CreateMembership,
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
    clock: ClockDep,
) -> schemas.MembershipRead:
    """Put the first person into an organisation.

    Every other membership is added by an org admin, and a freshly provisioned
    organisation has none: the console could provision, rename and suspend an
    organisation but could not seat its owner, so the first row had to be
    inserted by hand. A platform admin holds no org role, so this is the one
    membership write that does not go through `OrgAdmin`.
    """
    return await service_memberships.add_membership(
        session,
        workspace.org_id,
        email=body.email,
        role=body.role,
        product_surface=body.product_surface,
        actor=admin,
        now=clock.now(),
    )


@router.get(
    "/platform/overview",
    response_model=schemas.PlatformOverview,
    responses=error_responses(Forbidden),
)
async def read_overview(admin: PlatformAdmin, session: Session) -> schemas.PlatformOverview:
    """The numbers the console opens with, counted rather than listed."""
    return await service_platform.overview(session)


@router.get(
    "/platform/organizations/{org_slug}/memberships",
    response_model=Page[schemas.MembershipRead],
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def list_org_memberships_for_support(
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
) -> Page[schemas.MembershipRead]:
    """Read-only member list for platform support."""
    _ = admin
    items, next_cursor = await service_memberships.list_memberships(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


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
    items, next_cursor = await service.list_audit(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


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
    items, next_cursor = await service_platform.list_audit(
        session,
        org_slug=org_slug,
        actor_email=actor_email,
        action=action,
        limit=page.limit,
        cursor=page.cursor,
    )
    return Page(items=items, next_cursor=next_cursor)
