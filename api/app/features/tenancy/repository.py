"""Storage for organisations, memberships and the audit log.

Every org-scoped method takes `org_id` first. That is not a style preference:
it is the reason a cross-tenant read has to be written deliberately rather than
reached by forgetting a filter, which is how `b2b` leaked through
`find_slot_by_id_global`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, literal, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import encode_cursor
from app.features.tenancy.models import AuditEntry, Membership, Organization


async def create_organization(
    session: AsyncSession, *, slug: str, name: str, org_type: str = "institution", status: str = "trial"
) -> Organization:
    org = Organization(slug=slug.strip(), name=name, org_type=org_type, status=status)
    session.add(org)
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


async def membership_by_id(
    session: AsyncSession, org_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership | None:
    stmt = select(Membership).where(Membership.org_id == org_id, Membership.id == membership_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_memberships(
    session: AsyncSession, org_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[Membership], str | None]:
    stmt = select(Membership).where(Membership.org_id == org_id)
    return await _paginate(session, stmt, Membership, limit=limit, cursor=cursor, descending=False)


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
    return await _paginate(session, stmt, AuditEntry, limit=limit, cursor=cursor, descending=True)


# --- shared paging ---------------------------------------------------------


async def _paginate(
    session: AsyncSession,
    stmt: Select[Any],
    model: Any,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    descending: bool,
) -> tuple[list[Any], str | None]:
    """Keyset paging on (timestamp, id).

    The id breaks ties, because rows written in one transaction share a `now()`
    and would otherwise page non-deterministically — repeating or skipping rows
    across pages. Among simultaneous rows the order is stable but arbitrary;
    they happened at the same instant, so there is no true order to preserve.
    """
    sort_col = model.at if model is AuditEntry else model.created_at
    if cursor:
        mark, mark_id = datetime.fromisoformat(cursor["t"]), uuid.UUID(cursor["i"])
        # `tuple_()`, not a Python tuple: `(col_a, col_b) > (x, y)` compares the
        # Column objects in Python and silently produces the wrong filter.
        keyset = tuple_(sort_col, model.id)
        mark_tuple = tuple_(literal(mark), literal(mark_id))
        stmt = stmt.where(keyset < mark_tuple if descending else keyset > mark_tuple)
    order = (sort_col.desc(), model.id.desc()) if descending else (sort_col.asc(), model.id.asc())
    rows = list((await session.execute(stmt.order_by(*order).limit(limit + 1))).scalars())
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    last = page[-1]
    next_cursor = encode_cursor(
        {"t": (last.at if model is AuditEntry else last.created_at), "i": str(last.id)}
    )
    return page, next_cursor
