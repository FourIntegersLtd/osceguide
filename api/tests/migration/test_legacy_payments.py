"""Legacy payments imported from Firestore user records get their platform plan and price.

Regression: `plan_type` (`one_month`) was looked up as a plan code (`sca_1m`), so every
payment imported with no plan and 0p, and re-running skipped them as already imported.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan
from app.migration import loader
from app.migration.load_legacy_b2c import load_legacy_payments
from app.migration.users import (
    LEGACY_PRODUCT_TO_EXAM,
    PLAN_SUFFIX_BY_LEGACY_PLAN_TYPE,
    legacy_payment_for,
    merge_users,
)
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

PRICES = {"1m": 2499, "3m": 5999, "6m": 8999}


async def seed_plans(db: AsyncSession) -> dict[str, Plan]:
    plans: dict[str, Plan] = {}
    for exam in LEGACY_PRODUCT_TO_EXAM.values():
        for suffix, pence in PRICES.items():
            code = f"{exam}_{suffix}"
            plans[code] = Plan(
                code=code,
                stripe_price_id=f"price_{code}",
                exam_code=exam,
                amount_pence=pence,
                duration_days=30,
            )
    db.add_all(plans.values())
    await db.flush()
    return plans


def paid_record(app_type: str, plan_type: str | None, doc_id: str = "fs-1") -> dict:
    return {
        "id": doc_id,
        "email": "alice@example.com",
        "app_type": app_type,
        "username": "Alice",
        "created_at": "2026-01-15T09:00:00Z",
        "has_paid": True,
        "plan_type": plan_type,
        "plan_start_date": "2026-02-01T00:00:00Z",
        "stripe_payment_intent_id": f"pi_{doc_id}",
    }


async def import_payment(db: AsyncSession, record: dict):
    _, _, email_ids = await loader.load_users(db, merge_users([record]))
    payment = legacy_payment_for(record)
    assert payment is not None
    return await load_legacy_payments(db, [payment], user_ids=email_ids), payment, email_ids


async def stored(db: AsyncSession, intent: str) -> Payment:
    row = await db.scalar(select(Payment).where(Payment.stripe_payment_intent_id == intent))
    assert row is not None
    return row


async def test_one_month_sca_gets_its_plan_and_price(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")
    plans = await seed_plans(db_session)

    report, _, _ = await import_payment(db_session, paid_record("sca", "one_month"))

    row = await stored(db_session, "pi_fs-1")
    assert (row.plan_id, row.amount_total_pence) == (plans["sca_1m"].id, 2499)
    assert report.has_no_problems, report.problems


async def test_six_month_plab_resolves_to_plab_6m(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "plab")
    plans = await seed_plans(db_session)

    await import_payment(db_session, paid_record("plab", "six_month"))

    row = await stored(db_session, "pi_fs-1")
    assert (row.plan_id, row.amount_total_pence) == (plans["plab_6m"].id, 8999)


async def test_unknown_plan_type_is_imported_without_a_plan_and_reported(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")
    await seed_plans(db_session)

    report, _, _ = await import_payment(db_session, paid_record("sca", "lifetime"))

    row = await stored(db_session, "pi_fs-1")
    assert (row.plan_id, row.amount_total_pence) == (None, 0)
    assert len(report.problems) == 1
    assert "'lifetime'" in report.problems[0]


async def test_rerun_fills_a_row_imported_with_no_plan_and_no_amount(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")
    plans = await seed_plans(db_session)
    _, payment, email_ids = await import_payment(db_session, paid_record("sca", "one_month"))
    row = await stored(db_session, "pi_fs-1")
    row.plan_id, row.amount_total_pence = None, 0  # as the 164 wrongly imported rows are
    await db_session.flush()

    report = await load_legacy_payments(db_session, [payment], user_ids=email_ids)

    await db_session.refresh(row)
    assert (row.plan_id, row.amount_total_pence) == (plans["sca_1m"].id, 2499)
    assert (report.payments_created, report.payments_repaired) == (0, 1)
    again = await load_legacy_payments(db_session, [payment], user_ids=email_ids)
    assert again.payments_repaired == 0


async def test_rerun_leaves_a_row_that_already_has_a_plan_or_amount(db_session: AsyncSession) -> None:
    await ensure_exam(db_session, "sca")
    plans = await seed_plans(db_session)
    _, payment, email_ids = await import_payment(db_session, paid_record("sca", "one_month"))
    row = await stored(db_session, "pi_fs-1")
    row.plan_id, row.amount_total_pence = plans["sca_3m"].id, 1234
    await db_session.flush()

    report = await load_legacy_payments(db_session, [payment], user_ids=email_ids)

    await db_session.refresh(row)
    assert (row.plan_id, row.amount_total_pence) == (plans["sca_3m"].id, 1234)
    assert report.payments_repaired == 0

    row.plan_id = None  # a charged amount with no plan is real data too
    await db_session.flush()
    await load_legacy_payments(db_session, [payment], user_ids=email_ids)
    await db_session.refresh(row)
    assert (row.plan_id, row.amount_total_pence) == (None, 1234)


@pytest.mark.parametrize("plan_type", sorted(PLAN_SUFFIX_BY_LEGACY_PLAN_TYPE))
@pytest.mark.parametrize("product", sorted(LEGACY_PRODUCT_TO_EXAM))
def test_every_known_legacy_plan_type_names_a_platform_plan_code(product: str, plan_type: str) -> None:
    """The check that was missing: a mapped plan code must be shaped like `<exam>_<1m|3m|6m>`,
    the codes platform plans are sold under. The DB tests above prove they resolve once seeded."""
    payment = legacy_payment_for(paid_record(product, plan_type))
    assert payment is not None
    assert (
        payment.plan_code == f"{LEGACY_PRODUCT_TO_EXAM[product]}_{PLAN_SUFFIX_BY_LEGACY_PLAN_TYPE[plan_type]}"
    )
    assert payment.plan_code.split("_")[1] in {"1m", "3m", "6m"}
