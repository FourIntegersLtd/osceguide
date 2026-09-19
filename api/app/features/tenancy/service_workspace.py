"""Choosing a workspace, and what the chooser may then do.

Split from `service.py` only for reading size; it is the same slice and the
same public face, which is why `service` re-exports both of these.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal, issue_access_token
from app.core.settings import Settings
from app.core.tenancy import OrgSuspended
from app.features.tenancy import domain, repository
from app.features.tenancy.errors import NotAMember, OrgNotFound
from app.features.tenancy.schemas import Capabilities, WorkspaceToken
from app.features.tenancy.service import memberships_for_token


async def switch_workspace(
    session: AsyncSession,
    *,
    principal: Principal,
    org_slug: str | None,
    settings: Settings,
    now: datetime,
) -> WorkspaceToken:
    """Re-issue the token against another workspace.

    `org_slug=None` is the person's own practice, which is a workspace like any
    other — the same state a fresh login has before an organisation is chosen.
    Without it, joining an institution would be a one-way door.

    The memberships are read from the database, never copied from the presented
    token. Copying them made this a renewal machine: a revoked member or a
    demoted admin could call it every fourteen minutes and keep authority they
    no longer had, indefinitely, which is exactly what the fifteen-minute token
    exists to prevent. The organisation's status is checked here for the same
    reason.
    """
    memberships = await memberships_for_token(session, principal.user_id)

    if org_slug is None:
        personal = Principal(
            user_id=principal.user_id,
            email=principal.email,
            memberships=tuple(memberships),
            active_org_slug=None,
            is_platform_admin=principal.is_platform_admin,
            must_change_password=principal.must_change_password,
        )
        return WorkspaceToken(
            access_token=issue_access_token(personal, settings=settings, now=now),
            expires_in=settings.jwt_access_ttl_seconds,
            active_org_slug=None,
            active_role=None,
        )

    target = domain.resolve_workspace(
        [domain.MembershipRef(org_slug=m.org_slug, role=m.role, surface=m.surface) for m in memberships],
        org_slug,
    )
    if target is None:
        raise NotAMember()

    org = await repository.organization_by_slug(session, target.slug)
    if org is None:
        raise OrgNotFound()
    if not domain.org_permits_access(org.status) and not principal.is_platform_admin:
        raise OrgSuspended()

    switched = Principal(
        user_id=principal.user_id,
        email=principal.email,
        memberships=tuple(memberships),
        active_org_slug=target.slug,
        is_platform_admin=principal.is_platform_admin,
        must_change_password=principal.must_change_password,
    )
    return WorkspaceToken(
        access_token=issue_access_token(switched, settings=settings, now=now),
        expires_in=settings.jwt_access_ttl_seconds,
        active_org_slug=target.slug,
        active_role=target.role,
    )


def capabilities_for(principal: Principal) -> Capabilities:
    active = principal.active_membership
    role = active.role if active else None
    return Capabilities(
        user_id=principal.user_id,
        is_platform_admin=principal.is_platform_admin,
        active_org_slug=principal.active_org_slug,
        active_role=role,
        can={
            "read_org": domain.may_read_org(role),
            "manage_team": domain.is_org_admin(role),
            "run_circuits": domain.is_org_admin(role) or domain.is_assigned_staff(role),
            "sign_off_results": domain.is_institution_admin(role),
            "administer_platform": principal.is_platform_admin,
        },
    )
