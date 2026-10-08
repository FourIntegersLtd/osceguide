"""Storage for entitlements."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import false, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.entitlements.models import Entitlement


async def grant(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    source: str,
    source_ref: str | None = None,
    org_id: uuid.UUID | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    granted_by: uuid.UUID | None = None,
) -> Entitlement:
    """Insert one grant row and hand back the fresh entitlement, `starts_at`
    defaulting to the database's own `now()` if the caller does not name one."""
    entitlement = Entitlement(
        user_id=user_id,
        exam_id=exam_id,
        source=source,
        source_ref=source_ref,
        org_id=org_id,
        ends_at=ends_at,
        granted_by=granted_by,
        **({"starts_at": starts_at} if starts_at is not None else {}),
    )
    session.add(entitlement)
    await session.flush()
    await session.refresh(entitlement)
    return entitlement


async def for_user_and_exam(
    session: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID
) -> list[Entitlement]:
    """Every grant this user has ever held for this exam, oldest first — the
    raw material `domain.decide` weighs against `now`."""
    stmt = (
        select(Entitlement)
        .where(Entitlement.user_id == user_id, Entitlement.exam_id == exam_id)
        .order_by(Entitlement.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Entitlement]:
    """Every grant this user has ever held, oldest first, revoked and lapsed
    ones included."""
    stmt = select(Entitlement).where(Entitlement.user_id == user_id).order_by(Entitlement.created_at)
    return list((await session.execute(stmt)).scalars())


async def grants_by_source_for_org(
    session: AsyncSession, org_id: uuid.UUID, *, source: str
) -> list[Entitlement]:
    """What an institution has granted from one source, newest first, revoked and lapsed
    rows included. Org-scoped: `org_id` first."""
    stmt = (
        select(Entitlement)
        .where(Entitlement.org_id == org_id, Entitlement.source == source)
        .order_by(Entitlement.created_at.desc(), Entitlement.id)
    )
    return list((await session.execute(stmt)).scalars())


async def live_grant_from_org(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    exam_id: uuid.UUID,
    source: str,
    now: datetime,
) -> Entitlement | None:
    """A grant this organisation made that still gives this person this exam, if one does.

    Live means the same here as everywhere (`_live`): started, not ended, not revoked.
    """
    stmt = (
        select(Entitlement)
        .where(
            Entitlement.org_id == org_id,
            Entitlement.user_id == user_id,
            Entitlement.exam_id == exam_id,
            Entitlement.source == source,
            *_live(now),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def for_org(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None = None,
    matching_user_ids: Collection[uuid.UUID] | None = None,
    matching_exam_ids: Collection[uuid.UUID] | None = None,
    has_search: bool = False,
) -> tuple[list[Entitlement], str | None]:
    """A page of what an institution has granted, newest first. Org-scoped: `org_id` first.

    `matching_user_ids` and `matching_exam_ids` are ids `identity` and
    `catalog` already resolved from a search term (grantee name/email, or exam
    code); this never queries those tables itself. `has_search` distinguishes
    "no search was asked for" from "a search was asked for and matched
    nobody" — the latter must return no rows rather than every row.
    """
    stmt = select(Entitlement).where(Entitlement.org_id == org_id)
    if has_search:
        conditions = []
        if matching_user_ids:
            conditions.append(Entitlement.user_id.in_(list(matching_user_ids)))
        if matching_exam_ids:
            conditions.append(Entitlement.exam_id.in_(list(matching_exam_ids)))
        stmt = stmt.where(or_(*conditions) if conditions else false())
    return await keyset_page(
        session, stmt, sort_col=Entitlement.created_at, id_col=Entitlement.id, limit=limit, cursor=cursor
    )


async def by_id_for_org(
    session: AsyncSession, org_id: uuid.UUID, entitlement_id: uuid.UUID
) -> Entitlement | None:
    """One entitlement, scoped to the organisation that owns it: never
    returns another org's row even given its id."""
    stmt = select(Entitlement).where(Entitlement.org_id == org_id, Entitlement.id == entitlement_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def revoke(session: AsyncSession, entitlement_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(update(Entitlement).where(Entitlement.id == entitlement_id).values(revoked_at=at))


async def revoked_ids(session: AsyncSession, entitlement_ids: Collection[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these grants have been withdrawn."""
    if not entitlement_ids:
        return set()
    stmt = select(Entitlement.id).where(
        Entitlement.id.in_(list(entitlement_ids)), Entitlement.revoked_at.is_not(None)
    )
    return set((await session.execute(stmt)).scalars())


async def by_id(session: AsyncSession, entitlement_id: uuid.UUID) -> Entitlement | None:
    """Unscoped: for the platform console, which reads across every owner."""
    return (
        await session.execute(select(Entitlement).where(Entitlement.id == entitlement_id))
    ).scalar_one_or_none()


async def set_ends_at(session: AsyncSession, entitlement_id: uuid.UUID, *, ends_at: datetime | None) -> None:
    await session.execute(update(Entitlement).where(Entitlement.id == entitlement_id).values(ends_at=ends_at))


async def live_user_ids_for_exam(
    session: AsyncSession, exam_id: uuid.UUID, *, now: datetime
) -> set[uuid.UUID]:
    """Everyone holding a live grant for this exam.

    The liveness rule is `domain.Grant.live_at`, written here in SQL because
    the directory needs the whole set at once rather than a decision per row.
    A change to one must be made to the other.
    """
    stmt = select(Entitlement.user_id).where(Entitlement.exam_id == exam_id, *_live(now)).distinct()
    return set((await session.execute(stmt)).scalars())


async def live_for_users(
    session: AsyncSession, user_ids: Collection[uuid.UUID], *, now: datetime
) -> list[Entitlement]:
    """Every live grant among these users, in one query rather than one per
    person."""
    if not user_ids:
        return []
    stmt = select(Entitlement).where(Entitlement.user_id.in_(list(user_ids)), *_live(now))
    return list((await session.execute(stmt)).scalars())


def _live(now: datetime) -> tuple[Any, ...]:
    """The liveness rule as SQL predicates, so a caller can filter a whole
    directory at once rather than loading rows to ask `Grant.live_at` of
    each. A change here must be made to `domain.Grant.live_at` as well."""
    return (
        Entitlement.revoked_at.is_(None),
        Entitlement.starts_at <= now,
        or_(Entitlement.ends_at.is_(None), Entitlement.ends_at > now),
    )


async def purchases_ending_between(
    session: AsyncSession, *, after: datetime, before: datetime
) -> list[Entitlement]:
    """Bought access, not revoked, that ends in `(after, before]`: who is owed a warning."""
    stmt = (
        select(Entitlement)
        .where(
            Entitlement.source == "purchase",
            Entitlement.revoked_at.is_(None),
            Entitlement.ends_at > after,
            Entitlement.ends_at <= before,
        )
        .order_by(Entitlement.ends_at, Entitlement.id)
    )
    return list((await session.execute(stmt)).scalars())


async def has_later_access(session: AsyncSession, grant: Entitlement, *, now: datetime) -> bool:
    """Whether the same person holds other live access to the same exam, from any source,
    that never ends or ends after `grant` does."""
    assert grant.ends_at is not None
    stmt = (
        select(Entitlement.id)
        .where(
            Entitlement.user_id == grant.user_id,
            Entitlement.exam_id == grant.exam_id,
            Entitlement.id != grant.id,
            or_(Entitlement.ends_at.is_(None), Entitlement.ends_at > grant.ends_at),
            *_live(now),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).first() is not None
