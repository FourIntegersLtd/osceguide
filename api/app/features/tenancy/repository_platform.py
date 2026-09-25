"""The console's storage: the reads that deliberately cross every tenant.

Mapped classes never leave the repository; this is part of it.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.tenancy.models import AuditEntry, Organization


async def list_organizations(
    session: AsyncSession, *, limit: int, cursor: dict[str, Any] | None = None, status: str | None = None
) -> tuple[list[Organization], str | None]:
    """Every organisation. Deliberately not org-scoped: this is the console."""
    stmt = select(Organization)
    if status is not None:
        stmt = stmt.where(Organization.status == status)
    return await keyset_page(
        session,
        stmt,
        sort_col=Organization.created_at,
        id_col=Organization.id,
        limit=limit,
        cursor=cursor,
        descending=False,
    )


async def organizations_with_contracts(
    session: AsyncSession, *, statuses: Sequence[str]
) -> list[Organization]:
    """Every organisation in these statuses that has a contract end date at all."""
    stmt = select(Organization).where(
        Organization.status.in_(list(statuses)), Organization.contract_ends_at.is_not(None)
    )
    return list((await session.execute(stmt)).scalars())


async def organizations_in_statuses(session: AsyncSession, *, statuses: Sequence[str]) -> list[Organization]:
    """Every organisation in these statuses, contract or no contract."""
    stmt = select(Organization).where(Organization.status.in_(list(statuses))).order_by(Organization.name)
    return list((await session.execute(stmt)).scalars())


async def count_organizations_by_status(session: AsyncSession) -> dict[str, int]:
    stmt = select(Organization.status, func.count()).group_by(Organization.status)
    return {str(status): int(n) for status, n in (await session.execute(stmt)).all()}


async def list_audit_across_orgs(
    session: AsyncSession,
    *,
    org_id: uuid.UUID | None,
    actor_email: str | None,
    action: str | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[AuditEntry], str | None]:
    """The whole audit log, newest first, optionally narrowed.

    `org_id` is a filter here rather than a scope — the platform's own acts
    have none, and until this read existed nothing could see them. It is
    first all the same, so the guard that keeps every other audit read
    tenant-scoped is satisfied by shape and not by exception.
    """
    stmt = select(AuditEntry)
    if org_id is not None:
        stmt = stmt.where(AuditEntry.org_id == org_id)
    if actor_email:
        stmt = stmt.where(AuditEntry.actor_email.ilike(actor_email.strip()))
    if action:
        stmt = stmt.where(AuditEntry.action.like(f"{action.strip()}%"))
    return await keyset_page(
        session, stmt, sort_col=AuditEntry.at, id_col=AuditEntry.id, limit=limit, cursor=cursor
    )


async def list_audit_about_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[AuditEntry], str | None]:
    """Everything done to this person, and everything they did, newest first."""
    stmt = select(AuditEntry).where(
        or_(
            AuditEntry.actor_user_id == user_id,
            (AuditEntry.target_type == "user") & (AuditEntry.target_id == str(user_id)),
        )
    )
    return await keyset_page(
        session, stmt, sort_col=AuditEntry.at, id_col=AuditEntry.id, limit=limit, cursor=cursor
    )
