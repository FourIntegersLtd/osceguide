"""Storage for organisations, memberships and the audit log.

Every org-scoped method takes `org_id` first. That is not a style preference:
it is the reason a cross-tenant read has to be written deliberately rather than
reached by forgetting a filter, which is how `b2b` leaked through
`find_slot_by_id_global`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.tenancy.models import AuditEntry, Membership, Organization


async def create_organization(
    session: AsyncSession, *, slug: str, name: str, org_type: str = "institution", status: str = "trial"
) -> Organization:
    org = Organization(slug=slug.strip(), name=name, org_type=org_type, status=status)
    session.add(org)
    # Flushed and refreshed so the caller gets the generated id and the
    # server-side defaults (created_at, status) rather than None.
    await session.flush()
    await session.refresh(org)
    return org


async def organization_by_slug(session: AsyncSession, slug: str) -> Organization | None:
    stmt = select(Organization).where(Organization.slug == slug.strip())
    return (await session.execute(stmt)).scalar_one_or_none()


async def organization_by_id(session: AsyncSession, org_id: uuid.UUID) -> Organization | None:
    return (await session.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()


async def set_organization_status(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str,
    suspended_at: datetime | None = None,
    suspended_by: uuid.UUID | None = None,
) -> None:
    await session.execute(
        update(Organization)
        .where(Organization.id == org_id)
        .values(status=status, suspended_at=suspended_at, suspended_by=suspended_by)
    )


# --- memberships -----------------------------------------------------------


async def add_membership(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    product_surface: str | None = None,
) -> Membership:
    membership = Membership(org_id=org_id, user_id=user_id, role=role, product_surface=product_surface)
    session.add(membership)
    # Flushed so the caller gets the id and the server-side status: returned
    # unflushed, the row read back as `id=None` and the route serialising it
    # failed after the insert had already been written.
    await session.flush()
    await session.refresh(membership)
    return membership


async def memberships_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Membership]:
    """Not org-scoped by design: this answers "which orgs is this person in?",
    which is what login needs before any workspace exists."""
    stmt = (
        select(Membership)
        .where(Membership.user_id == user_id, Membership.revoked_at.is_(None))
        .order_by(Membership.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def live_memberships_with_orgs(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Membership, Organization]]:
    """A person's memberships and the organisations they are in, in one query.

    Was a query per membership, on every login and every refresh. The join also
    drops memberships whose organisation has gone, which the two-step version
    silently kept as a `None` org.
    """
    stmt = (
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.org_id)
        .where(
            Membership.user_id == user_id,
            Membership.revoked_at.is_(None),
            Membership.status != "revoked",
        )
        .order_by(Membership.created_at, Membership.id)
    )
    return [(membership, organization) for membership, organization in (await session.execute(stmt)).all()]


async def membership_for_user_in_org(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, *, role: str
) -> Membership | None:
    stmt = select(Membership).where(
        Membership.org_id == org_id, Membership.user_id == user_id, Membership.role == role
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def membership_by_id(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership | None:
    stmt = select(Membership).where(Membership.org_id == org_id, Membership.id == membership_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Membership], str | None]:
    stmt = select(Membership).where(Membership.org_id == org_id)
    return await keyset_page(
        session,
        stmt,
        sort_col=Membership.created_at,
        id_col=Membership.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def set_membership_role(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID, *, role: str
) -> None:
    await session.execute(
        update(Membership)
        .where(Membership.org_id == org_id, Membership.id == membership_id)
        .values(role=role)
    )


async def set_membership_revoked(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID, *, at: datetime | None
) -> None:
    await session.execute(
        update(Membership)
        .where(Membership.org_id == org_id, Membership.id == membership_id)
        .values(revoked_at=at, status="revoked" if at else "active")
    )


# --- audit -----------------------------------------------------------------


async def write_audit(
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
) -> AuditEntry:
    entry = AuditEntry(
        org_id=org_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        meta=meta,
        **({"at": at} if at is not None else {}),
    )
    session.add(entry)
    return entry


async def list_audit(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[AuditEntry], str | None]:
    stmt = select(AuditEntry).where(AuditEntry.org_id == org_id)
    return await keyset_page(
        session, stmt, sort_col=AuditEntry.at, id_col=AuditEntry.id, limit=limit, cursor=cursor
    )


async def count_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, roles: Sequence[str] | None = None
) -> int:
    """Live members, optionally of certain roles. Revoked people are not staff."""
    stmt = (
        select(func.count())
        .select_from(Membership)
        .where(Membership.org_id == org_id, Membership.revoked_at.is_(None))
    )
    if roles is not None:
        stmt = stmt.where(Membership.role.in_(list(roles)))
    return int((await session.execute(stmt)).scalar_one())


async def count_organizations(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Organization))).scalar_one())


async def update_organization(session: AsyncSession, org_id: uuid.UUID, **values: Any) -> None:
    await session.execute(update(Organization).where(Organization.id == org_id).values(**values))
