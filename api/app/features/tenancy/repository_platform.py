"""The console's storage: the reads that deliberately cross every tenant.

Separated from `repository.py` because these are the only queries in the
slice that are *not* org-scoped, and a file named for that is a better answer
to "why has this no `org_id`?" than a comment on each one. Mapped classes
still never leave the repository; this is part of it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.tenancy.models import Organization


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
