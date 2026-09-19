"""Tenancy use cases, and the membership lookup `identity` depends on."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership as TokenMembership
from app.core.auth import Principal
from app.core.tenancy import OrgRef
from app.features.tenancy import domain, repository
from app.features.tenancy.errors import OrgNotFound, OrgSlugTaken
from app.features.tenancy.schemas import AuditRead, OrganizationRead

# Re-exported so routers can build their access dependencies without importing
# the domain module directly: the service is the slice's public face.
is_org_admin = domain.is_org_admin
is_institution_admin = domain.is_institution_admin
is_assigned_staff = domain.is_assigned_staff
may_read_org = domain.may_read_org
may_run_circuit = domain.may_run_circuit
org_permits_access = domain.org_permits_access


async def org_ref_by_slug(session: AsyncSession, slug: str) -> OrgRef | None:
    org = await repository.organization_by_slug(session, slug)
    return None if org is None else OrgRef(id=org.id, slug=org.slug, status=org.status)


@dataclass(frozen=True)
class OrgSummary:
    """An organisation as another slice names it to a person: the id and a name."""

    id: uuid.UUID
    slug: str
    name: str
    status: str


async def org_ref_by_id(session: AsyncSession, org_id: uuid.UUID) -> OrgSummary | None:
    org = await repository.organization_by_id(session, org_id)
    return None if org is None else OrgSummary(id=org.id, slug=org.slug, name=org.name, status=org.status)


async def memberships_for_token(session: AsyncSession, user_id: uuid.UUID) -> list[TokenMembership]:
    """The claims form of a user's memberships.

    Returns the token's shape, not the table's: a mapped row would drag lazy
    relationships into a JWT, and the claims carry only what authorisation
    needs — org, slug, role, surface. `org_name` rides along for `GET /me` and
    is deliberately not a claim.
    """
    return [
        TokenMembership(
            org_id=org.id,
            org_slug=org.slug,
            role=row.role,
            surface=row.product_surface,
            org_name=org.name,
        )
        for row, org in await repository.live_memberships_with_orgs(session, user_id)
    ]


def default_workspace_for(memberships: list[TokenMembership]) -> str | None:
    """Which workspace a fresh token lands in.

    `identity` builds the principal and sits below this slice, so the rule is
    bound in `main.py` rather than imported. Three separate copies of
    `memberships[0]` used to decide this while `pick_default_workspace`, the
    rule written and tested for it, had no caller at all.
    """
    picked = domain.pick_default_workspace(
        [domain.MembershipRef(org_slug=m.org_slug, role=m.role, surface=m.surface) for m in memberships],
        preferred_order=(),
    )
    return picked.slug if picked else None


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


# Choosing a workspace and reading what the chooser may do live in
# `service_workspace.py`, which imports from here. The router calls that module
# directly rather than going through a re-export, so the dependency runs one
# way and there is no import cycle to work around.

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
