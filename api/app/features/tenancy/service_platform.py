"""The platform console: the organisations, as the people who run the product see them.

One of the two places in the API that read across tenants (the other is
`service_platform_users`). Everything else takes an `org_id` obtained by proving
membership; these functions take none, which is why every route that reaches
them is behind `PlatformAdmin`.

There is no delete: an organisation's rows include candidate results, which
exist to be defensible months later, and a cascade would take them. Suspension
is the reversible mechanism offered instead.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.tenancy import domain, repository, repository_platform
from app.features.tenancy.errors import ContractDatesOutOfOrder, ContractEndInPast, OrgNotFound
from app.features.tenancy.models import AuditEntry
from app.features.tenancy.schemas import (
    OrganizationRead,
    OrgAtRisk,
    PlatformAuditRead,
    PlatformOverview,
    RenewContract,
    UpdateOrganization,
)
from app.features.tenancy.service import _org_read, set_require_staff_mfa

# How far ahead "ending soon" looks. Thirty days is what b2b's console used
# for its at-risk list, and a renewal conversation takes about that long.
ENDING_SOON = timedelta(days=30)


async def list_organizations(
    session: AsyncSession,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    status: str | None = None,
    search: str | None = None,
    org_type: str | None = None,
) -> tuple[list[OrganizationRead], str | None]:
    """A page of every organisation on the platform, optionally filtered by
    status and type, or narrowed to names and slugs containing `search`."""
    organizations, next_cursor = await repository_platform.list_organizations(
        session, limit=limit, cursor=cursor, status=status, search=search, org_type=org_type
    )
    return [_org_read(org) for org in organizations], next_cursor


async def update_organization(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    changes: UpdateOrganization,
    actor: Principal,
    now: datetime,
) -> OrganizationRead:
    """Rename an organisation, change its type, or record its contract dates.

    Not the slug: every foreign key points at `id`, and the slug is the URL identifier, so
    renaming it is a redirect problem rather than a field edit.
    """
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()

    values = changes.model_dump(exclude_unset=True)
    if not domain.contract_dates_in_order(
        values.get("contract_starts_at", org.contract_starts_at),
        values.get("contract_ends_at", org.contract_ends_at),
    ):
        raise ContractDatesOutOfOrder()
    if "require_staff_mfa" in values:
        required = bool(values.pop("require_staff_mfa"))
        await set_require_staff_mfa(session, org_id, required=required, actor=actor, now=now)
    if values:
        await repository.update_organization(session, org_id, **values)
        await repository.write_audit(
            session,
            org_id=org_id,
            actor_user_id=actor.user_id,
            actor_email=actor.email,
            action="organization.updated",
            target_type="organization",
            target_id=str(org_id),
            summary=", ".join(sorted(values)),
        )
    refreshed = await repository.organization_by_id(session, org_id)
    return _org_read(refreshed)


async def restore_organization(
    session: AsyncSession, *, org_id: uuid.UUID, actor: Principal, now: datetime
) -> OrganizationRead:
    """Lift a suspension.

    A lapsed end date is cleared with it: left in place, the hourly sweep would suspend the
    organisation again within the hour. A future end date is kept.
    """
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
    if domain.contract_lapsed(org.contract_ends_at, now=now):
        await repository.update_organization(session, org_id, contract_ends_at=None)
    await repository.set_organization_status(
        session, org_id, status="active", suspended_at=None, suspended_by=None
    )
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="organization.restored",
        target_type="organization",
        target_id=str(org_id),
        summary=f"Restored at {now.isoformat()}",
    )
    refreshed = await repository.organization_by_id(session, org_id)
    return _org_read(refreshed)


async def overview(session: AsyncSession, *, now: datetime) -> PlatformOverview:
    """The numbers the console opens with, and the organisations to look at first.

    Counts, not lists, except `at_risk`: suspended, lapsed and not yet swept, or ending
    within thirty days.
    """
    return PlatformOverview(
        organizations=await repository.count_organizations(session),
        users=await identity.count_users(session),
        organizations_by_status=await repository_platform.count_organizations_by_status(session),
        at_risk=await _at_risk(session, now=now),
    )


async def _at_risk(session: AsyncSession, *, now: datetime) -> list[OrgAtRisk]:
    """Organisations the console should flag: suspended, or ending soon."""
    statuses = sorted(domain.ACTIVE_ORG_STATUSES | {"suspended"})
    at_risk_orgs: list[OrgAtRisk] = []
    for org in await repository_platform.organizations_in_statuses(session, statuses=statuses):
        if org.status == "suspended":
            reason = "suspended"
        elif domain.contract_lapsed(org.contract_ends_at, now=now):
            reason = "contract_lapsed"
        elif org.contract_ends_at is not None and org.contract_ends_at <= now + ENDING_SOON:
            reason = "contract_ending"
        else:
            continue
        at_risk_orgs.append(
            OrgAtRisk(
                slug=org.slug,
                name=org.name,
                status=org.status,
                contract_ends_at=org.contract_ends_at,
                reason=reason,
            )
        )
    return at_risk_orgs


async def renew_contract(
    session: AsyncSession, org_id: uuid.UUID, *, terms: RenewContract, actor: Principal, now: datetime
) -> OrganizationRead:
    """Record new contract dates and, unless told otherwise, lift the suspension.

    The lapse sweep suspends; this is its inverse, in one step rather than two, so the
    restore is never the step that gets forgotten.
    """
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
    if domain.contract_lapsed(terms.contract_ends_at, now=now):
        raise ContractEndInPast()
    values: dict[str, Any] = {"contract_ends_at": terms.contract_ends_at}
    if terms.contract_starts_at is not None:
        values["contract_starts_at"] = terms.contract_starts_at
    if not domain.contract_dates_in_order(
        values.get("contract_starts_at", org.contract_starts_at), terms.contract_ends_at
    ):
        raise ContractDatesOutOfOrder()
    await repository.update_organization(session, org_id, **values)
    restored = terms.restore and org.status == "suspended"
    if restored:
        await repository.set_organization_status(
            session, org_id, status="active", suspended_at=None, suspended_by=None
        )
    await repository.write_audit(
        session,
        org_id=org_id,
        actor_user_id=actor.user_id,
        actor_email=actor.email,
        action="organization.contract_renewed",
        at=now,
        target_type="organization",
        target_id=str(org_id),
        summary=f"Ends {terms.contract_ends_at:%Y-%m-%d}" + ("; restored" if restored else ""),
        meta={"contract_ends_at": terms.contract_ends_at.isoformat(), "restored": restored},
    )
    return _org_read(await repository.organization_by_id(session, org_id))


async def suspend_lapsed_organizations(session: AsyncSession, *, now: datetime) -> list[str]:
    """Suspend every organisation whose contract has ended. Returns their slugs.

    Run hourly by `jobs.py`.
    """
    lapsed: list[str] = []
    candidates = await repository_platform.organizations_with_contracts(
        session, statuses=sorted(domain.ACTIVE_ORG_STATUSES)
    )
    for org in candidates:
        if not domain.contract_lapsed(org.contract_ends_at, now=now):
            continue
        await repository.set_organization_status(session, org.id, status="suspended", suspended_at=now)
        await repository.write_audit(
            session,
            org_id=org.id,
            actor_user_id=None,
            actor_email=None,
            action="organization.contract_lapsed",
            at=now,
            target_type="organization",
            target_id=str(org.id),
            summary=f"Contract ended {org.contract_ends_at:%Y-%m-%d}; suspended",
        )
        lapsed.append(org.slug)
    return lapsed


# --- The audit log, read across every organisation.


async def list_audit(
    session: AsyncSession,
    *,
    org_slug: str | None,
    actor_email: str | None,
    action: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[PlatformAuditRead], str | None]:
    """The audit log across every organisation, plus platform-level rows that carry no
    organisation (who granted the console to whom, who deactivated an account)."""
    org_id: uuid.UUID | None = None
    if org_slug:
        org = await repository.organization_by_slug(session, org_slug)
        if org is None:
            raise OrgNotFound()
        org_id = org.id
    entries, next_cursor = await repository_platform.list_audit_across_orgs(
        session, org_id=org_id, actor_email=actor_email, action=action, limit=limit, cursor=cursor
    )
    return [platform_audit_read(entry) for entry in entries], next_cursor


def platform_audit_read(entry: AuditEntry) -> PlatformAuditRead:
    """Shape an audit entry into what a platform console route may return."""
    return PlatformAuditRead(
        id=entry.id,
        actor_email=entry.actor_email,
        action=entry.action,
        target_type=entry.target_type,
        target_id=entry.target_id,
        summary=entry.summary,
        at=entry.at,
        org_id=entry.org_id,
        actor_user_id=entry.actor_user_id,
        meta=entry.meta,
    )
