"""What the account directory knows about paying, for many people at once.

Kept apart from `service_platform.py`, which answers about one person's
payments in full. These are the facets — has this person ever paid, and what
did they last buy — that the console lists beside every row, and the sets the
directory filters by.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository_platform


@dataclass(frozen=True)
class PaymentFact:
    """The last thing somebody bought."""

    plan_code: str | None
    paid_at: datetime
    plan_ends_at: datetime | None


async def payer_ids(session: AsyncSession) -> set[uuid.UUID]:
    """Everyone who has ever paid — the directory's "paid" facet."""
    return await repository_platform.payer_user_ids(session)


async def payer_ids_on_plan(session: AsyncSession, plan_code: str) -> set[uuid.UUID]:
    return await repository_platform.payer_user_ids_on_plan(session, plan_code)


async def latest_payment_by_user(
    session: AsyncSession, user_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, PaymentFact]:
    rows = await repository_platform.latest_payments(session, user_ids)
    return {
        user_id: PaymentFact(plan_code=code, paid_at=paid_at, plan_ends_at=ends_at)
        for user_id, (code, paid_at, ends_at) in rows.items()
    }
