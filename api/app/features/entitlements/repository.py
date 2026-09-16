"""Storage for entitlements."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
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


async def revoke(session: AsyncSession, entitlement_id: uuid.UUID, *, at: datetime) -> None:
    await session.execute(update(Entitlement).where(Entitlement.id == entitlement_id).values(revoked_at=at))
