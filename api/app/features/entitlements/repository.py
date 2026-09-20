"""Storage for entitlements."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    row = Entitlement(
        user_id=user_id,
        exam_id=exam_id,
        source=source,
        source_ref=source_ref,
        org_id=org_id,
        ends_at=ends_at,
        granted_by=granted_by,
        **({"starts_at": starts_at} if starts_at is not None else {}),
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def for_user_and_exam(
    session: AsyncSession, user_id: uuid.UUID, exam_id: uuid.UUID
) -> list[Entitlement]:
    stmt = (
        select(Entitlement)
        .where(Entitlement.user_id == user_id, Entitlement.exam_id == exam_id)
        .order_by(Entitlement.created_at)
    )
    return list((await session.execute(stmt)).scalars())


async def for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Entitlement]:
    stmt = select(Entitlement).where(Entitlement.user_id == user_id).order_by(Entitlement.created_at)
    return list((await session.execute(stmt)).scalars())


async def for_org(session: AsyncSession, org_id: uuid.UUID) -> list[Entitlement]:
    """What an institution has granted. Org-scoped: `org_id` first."""
    stmt = select(Entitlement).where(Entitlement.org_id == org_id).order_by(Entitlement.created_at.desc())
    return list((await session.execute(stmt)).scalars())


async def by_id_for_org(
    session: AsyncSession, org_id: uuid.UUID, entitlement_id: uuid.UUID
) -> Entitlement | None:
    stmt = select(Entitlement).where(Entitlement.org_id == org_id, Entitlement.id == entitlement_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def revoke(session: AsyncSession, entitlement_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(update(Entitlement).where(Entitlement.id == entitlement_id).values(revoked_at=at))


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
    if not user_ids:
        return []
    stmt = select(Entitlement).where(Entitlement.user_id.in_(list(user_ids)), *_live(now))
    return list((await session.execute(stmt)).scalars())


def _live(now: datetime) -> tuple[Any, ...]:
    return (
        Entitlement.revoked_at.is_(None),
        Entitlement.starts_at <= now,
        or_(Entitlement.ends_at.is_(None), Entitlement.ends_at > now),
    )
