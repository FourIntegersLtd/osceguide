"""The platform console's membership routes. Every one of them is `PlatformAdmin`.

A platform admin holds no org role and does not inherit one — `OrgAdmin` is built with
`allow_platform_admin=False`, deliberately. Each write here goes through the same service
the organisation's own administrators use, so the audit row and the rules are the same;
only the door is different.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.tenancy import OrgReader, PlatformAdmin
from app.features.tenancy import errors, schemas, service_memberships

router = APIRouter(tags=["tenancy"])

Session = Annotated[AsyncSession, Depends(get_session)]


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
    memberships, next_cursor = await service_memberships.list_memberships(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=memberships, next_cursor=next_cursor)


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
    """Put somebody into an organisation from the console.

    Usually the first person: a freshly provisioned organisation has no admin
    to do it. Not only the first — the admin who left before naming a
    successor leaves the same gap, and an address with no account is invited
    exactly as an org admin's invitation would.
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


@router.patch(
    "/platform/organizations/{org_slug}/memberships/{membership_id}",
    response_model=schemas.MembershipRead,
    responses=error_responses(
        Forbidden, errors.OrgNotFound, errors.MembershipNotFound, errors.LastAdministrator
    ),
)
async def change_membership_role_for_support(
    membership_id: uuid.UUID,
    body: schemas.UpdateMembership,
    workspace: OrgReader,
    admin: PlatformAdmin,
    session: Session,
) -> schemas.MembershipRead:
    """The wrong person is the administrator: move the role."""
    return await service_memberships.change_membership_role(
        session, workspace.org_id, membership_id, role=body.role, actor=admin
    )


@router.post(
    "/platform/organizations/{org_slug}/memberships/{membership_id}/revoke",
    response_model=schemas.MembershipRead,
    responses=error_responses(
        Forbidden, errors.OrgNotFound, errors.MembershipNotFound, errors.LastAdministrator
    ),
)
async def revoke_membership_for_support(
    membership_id: uuid.UUID, workspace: OrgReader, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.MembershipRead:
    """Revoked, not deleted: the record of who had access and when survives."""
    return await service_memberships.set_membership_revoked(
        session, workspace.org_id, membership_id, revoked=True, actor=admin, now=clock.now()
    )


@router.post(
    "/platform/organizations/{org_slug}/memberships/{membership_id}/restore",
    response_model=schemas.MembershipRead,
    responses=error_responses(Forbidden, errors.OrgNotFound, errors.MembershipNotFound),
)
async def restore_membership_for_support(
    membership_id: uuid.UUID, workspace: OrgReader, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.MembershipRead:
    """The administrator who locked themselves out, let back in."""
    return await service_memberships.set_membership_revoked(
        session, workspace.org_id, membership_id, revoked=False, actor=admin, now=clock.now()
    )
