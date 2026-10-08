"""A plan on sale, for tests that buy one."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import repository as billing_repo
from tests.support.catalog import ensure_exam


async def a_plan(db_session: AsyncSession) -> None:
    # A plan names an exam by code rather than by key, so the plan can be
    # written before the exam is — but granting the purchase resolves it, and
    # nothing is seeded.
    await ensure_exam(db_session, "sca")
    await billing_repo.create_plan(
        db_session,
        code="one_month",
        stripe_price_id="price_one_month",
        amount_pence=2499,
        duration_days=30,
        exam_code="sca",
    )
    await db_session.flush()
