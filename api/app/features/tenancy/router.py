from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.settings import SettingsDep
from app.core.tenancy import OrgAdmin, OrgReader, PlatformAdmin
from app.features.tenancy import errors, schemas, service, service_memberships

router = APIRouter(tags=["tenancy"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/platform/organizations",
    response_model=schemas.OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.OrgSlugTaken),
)
async def provision_organization(
    body: schemas.CreateOrganization, admin: PlatformAdmin, session: Session
) -> schemas.OrganizationRead:
    return await service.provision_organization(
        session, slug=body.slug, name=body.name, org_type=body.org_type, actor=admin
    )


@router.post(
    "/platform/organizations/{org_slug}/suspend",
    response_model=schemas.OrganizationRead,
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def suspend_organization(
    workspace: OrgReader, admin: PlatformAdmin, session: Session, clock: ClockDep
) -> schemas.OrganizationRead:
    return await service.suspend_organization(session, org_id=workspace.org_id, actor=admin, now=clock.now())


@router.get(
    "/orgs/{org_slug}",
    response_model=schemas.OrganizationRead,
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def read_organization(workspace: OrgReader, session: Session) -> schemas.OrganizationRead:
    return await service.read_organization(session, workspace.org_id)


@router.get(
    "/orgs/{org_slug}/memberships",
    response_model=Page[schemas.MembershipRead],
    responses=error_responses(Forbidden),
)
async def list_memberships(
    workspace: OrgAdmin, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.MembershipRead]:
    items, next_cursor = await service_memberships.list_memberships(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/memberships",
    response_model=schemas.MembershipRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, errors.MembershipExists),
)
async def add_membership(
    body: schemas.CreateMembership, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.MembershipRead:
    """Put somebody in this organisation, by the address an administrator knows.

    An address with no account is invited: the account is created and the
    person is emailed a link to choose a password. `invited` says which.
    """
    return await service_memberships.add_membership(
        session,
        workspace.org_id,
        email=body.email,
        role=body.role,
        product_surface=body.product_surface,
        actor=workspace.principal,
        now=clock.now(),
    )


@router.patch(
    "/orgs/{org_slug}/memberships/{membership_id}",
    response_model=schemas.MembershipRead,
    responses=error_responses(Forbidden, errors.MembershipNotFound),
)
async def change_membership_role(
    membership_id: uuid.UUID, body: schemas.UpdateMembership, workspace: OrgAdmin, session: Session
) -> schemas.MembershipRead:
    return await service_memberships.change_membership_role(
        session, workspace.org_id, membership_id, role=body.role, actor=workspace.principal
    )


@router.post(
    "/orgs/{org_slug}/memberships/{membership_id}/revoke",
    response_model=schemas.MembershipRead,
    responses=error_responses(Forbidden, errors.MembershipNotFound),
)
async def revoke_membership(
    membership_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.MembershipRead:
    """Revoked, not deleted: the record of who had access and when survives."""
    return await service_memberships.set_membership_revoked(
        session,
        workspace.org_id,
        membership_id,
        revoked=True,
        actor=workspace.principal,
        now=clock.now(),
    )


@router.post(
    "/orgs/{org_slug}/memberships/{membership_id}/restore",
    response_model=schemas.MembershipRead,
    responses=error_responses(Forbidden, errors.MembershipNotFound),
)
async def restore_membership(
    membership_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.MembershipRead:
    return await service_memberships.set_membership_revoked(
        session,
        workspace.org_id,
        membership_id,
        revoked=False,
        actor=workspace.principal,
        now=clock.now(),
    )


@router.get(
    "/orgs/{org_slug}/audit",
    response_model=Page[schemas.AuditRead],
    responses=error_responses(Forbidden),
)
async def list_audit(
    workspace: OrgAdmin, session: Session, page: Annotated[CursorParams, Depends()]
) -> Page[schemas.AuditRead]:
    items, next_cursor = await service.list_audit(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor
    )
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/auth/switch-workspace",
    response_model=schemas.WorkspaceToken,
    responses=error_responses(Unauthenticated, errors.NotAMember),
)
async def switch_workspace(
    body: schemas.SwitchWorkspace,
    principal: CurrentPrincipal,
    session: Session,
    settings: SettingsDep,
    clock: ClockDep,
) -> schemas.WorkspaceToken:
    return await service.switch_workspace(
        session, principal=principal, org_slug=body.org_slug, settings=settings, now=clock.now()
    )


@router.get(
    "/me/capabilities",
    response_model=schemas.Capabilities,
    responses=error_responses(Unauthenticated),
)
async def read_capabilities(principal: CurrentPrincipal) -> schemas.Capabilities:
    return service.capabilities_for(principal)
