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
    """The minimal organisation reference other slices use, by slug."""
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
    """An organisation's name and status, for another slice to display."""
    org = await repository.organization_by_id(session, org_id)
    return None if org is None else OrgSummary(id=org.id, slug=org.slug, name=org.name, status=org.status)


async def memberships_for_token(session: AsyncSession, user_id: uuid.UUID) -> list[TokenMembership]:
    """The claims form of a user's memberships.

    Returns the token's shape, not the table's: a mapped row would drag lazy
    relationships into a JWT, and the claims carry only what authorisation
    needs — org, slug, role, surface. `org_name` and `org_type` ride along for
    `GET /me` and are deliberately not claims.
    """
    return [
        TokenMembership(
            org_id=org.id,
            org_slug=org.slug,
            role=membership.role,
            surface=membership.product_surface,
            org_name=org.name,
            org_type=org.org_type,
        )
        for membership, org in await repository.live_memberships_with_orgs(session, user_id)
    ]


def default_workspace_for(memberships: list[TokenMembership]) -> str | None:
    """Which workspace a fresh token lands in."""
    picked = domain.pick_default_workspace(
        [
            domain.MembershipRef(
                org_slug=membership.org_slug, role=membership.role, surface=membership.surface
            )
            for membership in memberships
        ],
        preferred_order=(),
    )
    return picked.slug if picked else None


# --- organisations ---------------------------------------------------------


async def provision_organization(
    session: AsyncSession, *, slug: str, name: str, org_type: str, actor: Principal
) -> OrganizationRead:
    """Create a new organisation, refusing a slug that is already taken."""
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


async def staff_mfa_flags(session: AsyncSession, user_id: uuid.UUID) -> list[tuple[str, bool]]:
    """Each live membership's role and whether that organisation requires staff MFA.

    Identity asks for this at password sign-in. A revoked membership is absent,
    so leaving an organisation drops the requirement at the next sign-in.
    """
    return await repository.staff_mfa_flags(session, user_id)


async def record_audit(
    session: AsyncSession,
    *,
    org_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    actor_email: str | None,
    action: str,
    at: datetime | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Append one audit row. `org_id=None` is a platform event, not an organisation's."""
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        at=at,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        meta=meta,
    )


async def set_require_staff_mfa(
    session: AsyncSession, org_id: uuid.UUID, *, required: bool, actor: Principal, now: datetime
) -> OrganizationRead:
    """Require (or stop requiring) a second factor for this organisation's staff.

    Takes effect at the next password sign-in. Refresh chains already issued
    keep working until they expire or are revoked.
    """
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
    await repository.update_organization(session, org_id, require_staff_mfa=required)
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="org.mfa_policy_changed",
        at=now,
        target_type="organization",
        target_id=str(org_id),
        summary="Staff must use a second factor" if required else "Staff second factor is no longer required",
        meta={"require_staff_mfa": required},
    )
    refreshed = await repository.organization_by_id(session, org_id)
    return _org_read(refreshed)


async def read_organization(session: AsyncSession, org_id: uuid.UUID) -> OrganizationRead:
    """Fetch an organisation, or refuse if it does not exist."""
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
    return _org_read(org)


async def suspend_organization(
    session: AsyncSession, *, org_id: uuid.UUID, actor: Principal, now: datetime
) -> OrganizationRead:
    """Suspend an organisation, blocking its members' access until it is restored."""
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
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    actor_email: str | None = None,
    action: str | None = None,
) -> tuple[list[AuditRead], str | None]:
    """A page of one organisation's audit log, optionally narrowed to what one
    person did or to one kind of action."""
    entries, next_cursor = await repository.list_audit(
        session, org_id, limit=limit, cursor=cursor, actor_email=actor_email, action=action
    )
    return [
        AuditRead(
            id=entry.id,
            actor_email=entry.actor_email,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            summary=entry.summary,
            at=entry.at,
        )
        for entry in entries
    ], next_cursor


# Choosing a workspace and reading what the chooser may do live in
# `service_workspace.py`, which imports from here. The router calls that module
# directly rather than going through a re-export, so the dependency runs one
# way and there is no import cycle to work around.

# --- mapping ---------------------------------------------------------------


def _org_read(org: Any) -> OrganizationRead:
    """Shape an organisation row into what a route may return."""
    return OrganizationRead(
        id=org.id,
        slug=org.slug,
        name=org.name,
        org_type=org.org_type,
        status=org.status,
        created_at=org.created_at,
        contract_starts_at=org.contract_starts_at,
        contract_ends_at=org.contract_ends_at,
        require_staff_mfa=org.require_staff_mfa,
        parent_org_id=org.parent_org_id,
    )


async def grant_trainee_membership(session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Give a rostered person the `trainee` membership that makes the organisation theirs to open.

    Idempotent: a revoked trainee membership is reactivated, and somebody who already
    holds another live role here (a supervisor who is also rostered) is left alone.
    True when a membership was created or reactivated.
    """
    held = await repository.memberships_for_user_in_org(session, org_id, user_id)
    trainee_row = next((membership for membership in held if membership.role == domain.TRAINEE_ROLE), None)
    if trainee_row is not None:
        if trainee_row.revoked_at is None:
            return False
        await repository.set_membership_revoked(session, org_id, trainee_row.id, at=None)
        return True
    if any(membership.revoked_at is None for membership in held):
        return False
    await repository.add_membership(session, org_id=org_id, user_id=user_id, role=domain.TRAINEE_ROLE)
    return True


async def revoke_trainee_membership(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID | None, *, at: datetime
) -> None:
    """Revoke only the `trainee` membership; a staff role the same person holds stays."""
    if user_id is None:
        return
    membership = await repository.membership_for_user_in_org(
        session, org_id, user_id, role=domain.TRAINEE_ROLE
    )
    if membership is not None and membership.revoked_at is None:
        await repository.set_membership_revoked(session, org_id, membership.id, at=at)


async def member_user_ids(
    session: AsyncSession, org_id: uuid.UUID, user_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Which of these people are live members of the organisation, for the roster's status column."""
    return await repository.member_user_ids(session, org_id, user_ids)
