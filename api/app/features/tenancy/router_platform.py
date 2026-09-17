"""The platform console's routes. Every one of them is `PlatformAdmin`.

A router of its own because the access rule is uniform and unlike the rest of
the API: these read across tenants rather than inside one, and keeping them in
a file named for that makes "who can call this?" a question answered by where
the route lives.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgReader, PlatformAdmin
from app.features.tenancy import errors, schemas, service_platform

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


@router.get(
    "/platform/users",
    response_model=Page[schemas.UserSummary],
    responses=error_responses(Forbidden),
)
async def search_users(
    admin: PlatformAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    q: Annotated[str | None, Query(description="Part of an email address")] = None,
) -> Page[schemas.UserSummary]:
    """Find an account by email, for the people who answer "I cannot sign in"."""
    items, next_cursor = await service_platform.search_users(
        session, query=q, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.put(
    "/platform/users/{user_id}/platform-admin",
    response_model=schemas.UserSummary,
    responses=error_responses(Forbidden, errors.UserNotFound),
)
async def set_platform_admin(
    user_id: uuid.UUID,
    body: schemas.SetPlatformAdmin,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.UserSummary:
    """Grant or revoke the console itself. One route, because they are one
    decision and two would invite one of them to be forgotten."""
    return await service_platform.set_platform_admin(
        session, user_id, is_admin=body.is_platform_admin, actor=admin
    )


@router.get(
    "/platform/overview",
    response_model=schemas.PlatformOverview,
    responses=error_responses(Forbidden),
)
async def read_overview(admin: PlatformAdmin, session: Session) -> schemas.PlatformOverview:
    """The numbers the console opens with, counted rather than listed."""
    return await service_platform.overview(session)
