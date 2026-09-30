"""Routes for organisations and who belongs to them: provisioning and
suspending an organisation, its memberships and audit log, and switching
which workspace a signed-in person is acting in.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.pagination import CursorParams, Page
from app.core.ports import ClockDep
from app.core.rate_limit import OUTBOUND_EMAIL, TooManyRequests, per_user
from app.core.role_policy import policy
from app.core.settings import SettingsDep
from app.core.tenancy import OrgAdmin, OrgReader, PlatformAdmin, Workspace, require_org
from app.features.tenancy import (
    errors,
    schemas,
    service,
    service_bulk,
    service_memberships,
    service_workspace,
)
from app.features.tenancy.schemas import InvitationRead

router = APIRouter(tags=["tenancy"])

Session = Annotated[AsyncSession, Depends(get_session)]


# Provisions a new organisation on the platform.
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


InstitutionOrPlatform = Annotated[
    Workspace, Depends(require_org(policy("is_institution_admin"), allow_platform_admin=True))
]


# Institution admins of this organisation, and platform admins, require staff MFA.
@router.patch(
    "/orgs/{org_slug}/mfa-policy",
    response_model=schemas.OrganizationRead,
    responses=error_responses(Forbidden, errors.OrgNotFound),
)
async def set_staff_mfa_policy(
    body: schemas.StaffMfaPolicy,
    workspace: InstitutionOrPlatform,
    session: Session,
    clock: ClockDep,
) -> schemas.OrganizationRead:
    return await service.set_require_staff_mfa(
        session,
        workspace.org_id,
        required=body.require_staff_mfa,
        actor=workspace.principal,
        now=clock.now(),
    )


# A page of an organisation's memberships.
@router.get(
    "/orgs/{org_slug}/memberships",
    response_model=Page[schemas.MembershipRead],
    responses=error_responses(Forbidden),
)
async def list_memberships(
    workspace: OrgAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    search: Annotated[str | None, Query(description="A membership's email, role, or user id")] = None,
    status: Annotated[
        str | None, Query(pattern="^(active|revoked)$", description="Only memberships in this state.")
    ] = None,
) -> Page[schemas.MembershipRead]:
    memberships, next_cursor = await service_memberships.list_memberships(
        session, workspace.org_id, limit=page.limit, cursor=page.cursor, search=search, status=status
    )
    return Page(items=memberships, next_cursor=next_cursor)


@router.post(
    "/orgs/{org_slug}/memberships",
    response_model=schemas.MembershipRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(TooManyRequests, Forbidden, errors.MembershipExists),
    dependencies=[Depends(per_user(OUTBOUND_EMAIL))],
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


@router.post(
    "/orgs/{org_slug}/memberships/bulk",
    response_model=schemas.BulkMembershipsResult,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(TooManyRequests, Forbidden),
    dependencies=[Depends(per_user(OUTBOUND_EMAIL))],
)
async def add_memberships(
    body: schemas.BulkCreateMemberships, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkMembershipsResult:
    """A team at once: the browser parses the spreadsheet, this takes the rows.

    Each row is the single act below it, so an unknown address is invited and an existing
    one is not re-invited. A person already holding the role is reported in `skipped`
    rather than failing the other rows.
    """
    return await service_bulk.add_memberships(
        session, workspace.org_id, entries=body.memberships, actor=workspace.principal, now=clock.now()
    )


# Changes what role a membership holds.
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


# The two bulk routes below must stay registered before the `{membership_id}` routes
# they share a first path segment with ("revoke", "resend-invitation"): FastAPI matches
# path segments in registration order, so a `{membership_id}` route registered first
# would swallow "bulk" as the id and 422 on the UUID parse.
@router.post(
    "/orgs/{org_slug}/memberships/bulk/revoke",
    response_model=schemas.BulkMembershipRevokeResponse,
    responses=error_responses(Forbidden),
)
async def bulk_revoke_memberships(
    body: schemas.BulkMembershipIds, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkMembershipRevokeResponse:
    """Revoke a selection from the team table at once. Each row goes through the
    same `POST /memberships/{id}/revoke` decision; an id from another
    organisation, or repeated in the request, is reported rather than acted on twice.
    """
    results = await service_bulk.revoke_memberships(
        session, workspace.org_id, body.membership_ids, actor=workspace.principal, now=clock.now()
    )
    return schemas.BulkMembershipRevokeResponse(results=results)


@router.post(
    "/orgs/{org_slug}/memberships/bulk/resend-invitation",
    response_model=schemas.BulkMembershipInvitationResponse,
    responses=error_responses(Forbidden),
)
async def bulk_resend_membership_invitations(
    body: schemas.BulkMembershipIds, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> schemas.BulkMembershipInvitationResponse:
    """Resend the choose-a-password link to a selection at once, each row through
    the same `POST /memberships/{id}/resend-invitation` decision.
    """
    results = await service_bulk.resend_membership_invitations(
        session, workspace.org_id, body.membership_ids, now=clock.now()
    )
    return schemas.BulkMembershipInvitationResponse(results=results)


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


# Restores a previously revoked membership.
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


@router.post(
    "/orgs/{org_slug}/memberships/{membership_id}/resend-invitation",
    response_model=InvitationRead,
    responses=error_responses(
        TooManyRequests, Forbidden, errors.MembershipNotFound, errors.InvitationNotPending
    ),
    dependencies=[Depends(per_user(OUTBOUND_EMAIL))],
)
async def resend_membership_invitation(
    membership_id: uuid.UUID, workspace: OrgAdmin, session: Session, clock: ClockDep
) -> InvitationRead:
    """Send the choose-a-password link again, as a new token. Returns 409
    `invitation_not_pending` if the person has already chosen a password."""
    return await service_memberships.resend_invitation(
        session, workspace.org_id, membership_id, now=clock.now()
    )


# A page of an organisation's audit log.
@router.get(
    "/orgs/{org_slug}/audit",
    response_model=Page[schemas.AuditRead],
    responses=error_responses(Forbidden),
)
async def list_audit(
    workspace: OrgAdmin,
    session: Session,
    page: Annotated[CursorParams, Depends()],
    actor_email: Annotated[str | None, Query(description="Only what this person did")] = None,
    action: Annotated[
        str | None, Query(description="An action name, or its prefix such as `membership.`")
    ] = None,
) -> Page[schemas.AuditRead]:
    audit_entries, next_cursor = await service.list_audit(
        session,
        workspace.org_id,
        limit=page.limit,
        cursor=page.cursor,
        actor_email=actor_email,
        action=action,
    )
    return Page(items=audit_entries, next_cursor=next_cursor)


# Re-issues the signed-in person's token for another workspace.
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
    return await service_workspace.switch_workspace(
        session, principal=principal, org_slug=body.org_slug, settings=settings, now=clock.now()
    )


@router.get(
    "/me/capabilities",
    response_model=schemas.Capabilities,
    responses=error_responses(Unauthenticated),
)
async def read_capabilities(principal: CurrentPrincipal) -> schemas.Capabilities:
    return service_workspace.capabilities_for(principal)
