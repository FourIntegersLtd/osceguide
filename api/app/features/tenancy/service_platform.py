"""The platform console: the organisations, as the people who run the product see them.

Deliberately one of the two places in the API that read across tenants — the
other is `service_platform_users`, split off at the file cap along the line
between an organisation and a person. Everything
else takes an `org_id` obtained by proving membership; these functions take
none, which is why every route that reaches them is behind `PlatformAdmin` and
why they live in a module named for what they are.

The legacy console could delete an organisation. This one cannot, and that is a
decision rather than an omission: an organisation's rows include candidate
results, which exist to be defensible months later, and a cascade would take
them. Suspension is the reversible mechanism and it is what this offers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.identity import service as identity
from app.features.tenancy import domain, repository, repository_platform
from app.features.tenancy.errors import OrgNotFound
from app.features.tenancy.models import AuditEntry
from app.features.tenancy.schemas import (
    OrganizationRead,
    PlatformAuditRead,
    PlatformOverview,
    UpdateOrganization,
)
from app.features.tenancy.service import _org_read


async def list_organizations(
    session: AsyncSession, *, limit: int, cursor: dict[str, Any] | None, status: str | None = None
) -> tuple[list[OrganizationRead], str | None]:
    rows, next_cursor = await repository_platform.list_organizations(
        session, limit=limit, cursor=cursor, status=status
    )
    return [_org_read(row) for row in rows], next_cursor


async def update_organization(
    session: AsyncSession, org_id: uuid.UUID, *, changes: UpdateOrganization, actor: Principal
) -> OrganizationRead:
    """Rename an organisation, change its type, or record its contract dates.

    Not the slug: every foreign key in every slice points at `id`, and the slug
    is the URL identifier, so renaming one is a redirect problem rather than a
    field edit. b2b keyed on `org_slug` and could not rename anything at all.
    """
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()

    values = changes.model_dump(exclude_unset=True)
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

    Suspending was write-only in every sense: it restricted nobody until the
    org status started being read per request, and once it did there was no
    route to undo it. An action with no inverse is one nobody dares use.
    """
    org = await repository.organization_by_id(session, org_id)
    if org is None:
        raise OrgNotFound()
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


async def overview(session: AsyncSession) -> PlatformOverview:
    """The numbers the console opens with, counted rather than listed."""
    return PlatformOverview(
        organizations=await repository.count_organizations(session),
        users=await identity.count_users(session),
    )


async def suspend_lapsed_organizations(session: AsyncSession, *, now: datetime) -> list[str]:
    """Suspend every organisation whose contract has ended. Returns their slugs.

    Contract dates were stored and enforced by nothing, so a lapsed contract
    needed somebody to notice. Run hourly by `jobs.py`. Suspension is the
    existing, reversible mechanism: renewing is a `PATCH` of the end date and
    a `restore`, both of which already exist, and the audit row says why.
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


async def list_audit(
    session: AsyncSession,
    *,
    org_slug: str | None,
    actor_email: str | None,
    action: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
) -> tuple[list[PlatformAuditRead], str | None]:
    """The audit log across every organisation, and the platform's own rows.

    Those rows — who granted the console to whom, who deactivated an account —
    were written from the start with no organisation and, until this read
    existed, nothing could read them back.
    """
    org_id: uuid.UUID | None = None
    if org_slug:
        org = await repository.organization_by_slug(session, org_slug)
        if org is None:
            raise OrgNotFound()
        org_id = org.id
    rows, next_cursor = await repository_platform.list_audit_across_orgs(
        session, org_id=org_id, actor_email=actor_email, action=action, limit=limit, cursor=cursor
    )
    return [platform_audit_read(row) for row in rows], next_cursor


def platform_audit_read(row: AuditEntry) -> PlatformAuditRead:
    return PlatformAuditRead(
        id=row.id,
        actor_email=row.actor_email,
        action=row.action,
        target_type=row.target_type,
        target_id=row.target_id,
        summary=row.summary,
        at=row.at,
        org_id=row.org_id,
        actor_user_id=row.actor_user_id,
        meta=row.meta,
    )
