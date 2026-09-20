"""Storage reads the platform console asks about many payers at once.

Split from `repository.py` at the file cap. Nothing here is scoped to a
person: these are the answers to "who has paid?" and "what did each of these
people last buy?", which only the directory behind `PlatformAdmin` asks.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan


async def payer_user_ids(session: AsyncSession) -> set[uuid.UUID]:
    """Everyone with at least one payment. Unbounded on purpose: it is the
    directory's "paid" facet and has to be complete to be a facet at all."""
    stmt = select(Payment.user_id).distinct()
    return set((await session.execute(stmt)).scalars())


async def latest_payments(
    session: AsyncSession, user_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, tuple[str | None, datetime, datetime | None]]:
    """Each person's most recent payment: `(plan code, paid at, plan ends at)`."""
    if not user_ids:
        return {}
    newest = (
        select(Payment.user_id, func.max(Payment.paid_at).label("paid_at"))
        .where(Payment.user_id.in_(list(user_ids)))
        .group_by(Payment.user_id)
        .subquery()
    )
    stmt = (
        select(Payment.user_id, Plan.code, Payment.paid_at, Payment.plan_ends_at)
        .join(newest, (newest.c.user_id == Payment.user_id) & (newest.c.paid_at == Payment.paid_at))
        .outerjoin(Plan, Plan.id == Payment.plan_id)
    )
    return {
        user_id: (code, paid_at, ends_at)
        for user_id, code, paid_at, ends_at in (await session.execute(stmt)).all()
    }


async def payer_user_ids_on_plan(session: AsyncSession, plan_code: str) -> set[uuid.UUID]:
    """Everyone whose most recent payment bought this plan."""
    newest = (
        select(Payment.user_id, func.max(Payment.paid_at).label("paid_at"))
        .group_by(Payment.user_id)
        .subquery()
    )
    stmt = (
        select(Payment.user_id)
        .join(newest, (newest.c.user_id == Payment.user_id) & (newest.c.paid_at == Payment.paid_at))
        .join(Plan, Plan.id == Payment.plan_id)
        .where(Plan.code == plan_code)
    )
    return set((await session.execute(stmt)).scalars())
