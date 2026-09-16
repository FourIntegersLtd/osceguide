"""Tenancy use cases, and the membership lookup `identity` depends on."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership as TokenMembership
from app.core.auth import Principal
from app.core.settings import Settings
from app.core.tenancy import OrgRef
from app.features.tenancy import domain, repository
from app.features.tenancy.errors import (
    MembershipExists,
    NotAMember,
    OrgNotFound,
    OrgSlugTaken,
)
from app.features.tenancy.schemas import (
    AuditRead,
    Capabilities,
    MembershipRead,
    OrganizationRead,
    WorkspaceToken,
)

# Re-exported so routers can build their access dependencies without importing
# the domain module directly: the service is the slice's public face.
is_org_admin = domain.is_org_admin
is_institution_admin = domain.is_institution_admin
is_assigned_staff = domain.is_assigned_staff
may_read_org = domain.may_read_org
org_permits_access = domain.org_permits_access


async def org_ref_by_slug(session: AsyncSession, slug: str) -> OrgRef | None:
    org = await repository.organization_by_slug(session, slug)
    return None if org is None else OrgRef(id=org.id, slug=org.slug, status=org.status)


async def memberships_for_token(session: AsyncSession, user_id: uuid.UUID) -> list[TokenMembership]:
    """The claims form of a user's memberships.

    Returns the token's shape, not the table's: a mapped row would drag lazy
    relationships into a JWT, and the claims carry only what authorisation
    needs — org, slug, role, surface.
    """
    rows = await repository.memberships_for_user(session, user_id)
    out: list[TokenMembership] = []
    for row in rows:
        org = await repository.organization_by_id(session, row.org_id)
        if org is not None:
            out.append(
                TokenMembership(org_id=org.id, org_slug=org.slug, role=row.role, surface=row.product_surface)
            )
    return out


# --- organisations ---------------------------------------------------------


async def provision_organization(
    session: AsyncSession, *, slug: str, name: str, org_type: str, actor: Principal
) -> OrganizationRead:
    if await repository.organization_by_slug(session, slug) is not None:
        raise OrgSlugTaken()
    org = await repository.create_organization(session, slug=slug, name=name, org_type=org_type)
    await repository.write_audit(
        session,
        org_id=org.id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="organization.provisioned",
        target_type="organization",
        target_id=str(org.id),
        summary=f"Provisioned {org_type} {slug}",
    )
    return _org_read(org)


async def read_organization(session: AsyncSession, org_id: uuid.UUID) -> OrganizationRead:
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
    return _org_read(org)


async def suspend_organization(
    session: AsyncSession, *, org_id: uuid.UUID, actor: Principal, now: datetime
) -> OrganizationRead:
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
    await repository.set_organization_status(
        session, org_id, status="suspended", suspended_at=now, suspended_by=actor.user_id
    )
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="organization.suspended",
        target_type="organization",
        target_id=str(org_id),
    )
    refreshed = await repository.organization_by_id(session, org_id)
    return _org_read(refreshed)


# --- memberships -----------------------------------------------------------


async def list_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[MembershipRead], str | None]:
    rows, next_cursor = await repository.list_memberships(session, org_id, limit=limit, cursor=cursor)
    return [_membership_read(r) for r in rows], next_cursor


async def add_membership(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    role: str,
    product_surface: str | None,
    actor: Principal,
) -> MembershipRead:
    existing = await repository.memberships_for_user(session, user_id)
    if any(m.org_id == org_id and m.role == role for m in existing):
        raise MembershipExists()
    membership = await repository.add_membership(
        session, org_id=org_id, user_id=user_id, role=role, product_surface=product_surface
    )
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="membership.added",
        target_type="membership",
        target_id=str(user_id),
        summary=f"Granted {role}",
    )
    return _membership_read(membership)


async def list_audit(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[AuditRead], str | None]:
    rows, next_cursor = await repository.list_audit(session, org_id, limit=limit, cursor=cursor)
    return [
        AuditRead(
            id=r.id,
            actor_email=r.actor_email,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            summary=r.summary,
            at=r.at,
        )
        for r in rows
    ], next_cursor


# --- workspace and capabilities --------------------------------------------


async def switch_workspace(
    session: AsyncSession, *, principal: Principal, org_slug: str, settings: Settings, now: datetime
) -> WorkspaceToken:
    memberships = [
        domain.MembershipRef(org_slug=m.org_slug, role=m.role, surface=m.surface)
        for m in principal.memberships
    ]
    target = domain.resolve_workspace(memberships, org_slug)
    if target is None:
        raise NotAMember()

    from app.features.identity.tokens import access_token_for

    switched = Principal(
        user_id=principal.user_id,
        email=principal.email,
        memberships=principal.memberships,
        active_org_slug=target.slug,
        is_platform_admin=principal.is_platform_admin,
    )
    return WorkspaceToken(
        access_token=access_token_for(switched, settings=settings, now=now),
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


# --- mapping ---------------------------------------------------------------


def _org_read(org: Any) -> OrganizationRead:
    return OrganizationRead(
        id=org.id,
        slug=org.slug,
        name=org.name,
        org_type=org.org_type,
        status=org.status,
        created_at=org.created_at,
    )


def _membership_read(row: Any) -> MembershipRead:
    return MembershipRead(
        id=row.id,
        user_id=row.user_id,
        role=row.role,
        product_surface=row.product_surface,
        status=row.status,
        revoked_at=row.revoked_at,
    )
