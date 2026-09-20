"""Payments and referrals from B2C user documents."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan
from app.features.growth.models import Referral
from app.migration.report import LoadReport
from app.migration.users import MergedLegacyPayment, MergedReferral

LEGACY_CONSUMER_PROVIDER = "consumer"


async def load_legacy_payments(
    session: AsyncSession,
    payments: Sequence[MergedLegacyPayment],
    *,
    user_ids: dict[str, uuid.UUID],
) -> LoadReport:
    report = LoadReport()
    plans = {
        str(code).lower(): plan_id
        for code, plan_id in (await session.execute(select(Plan.code, Plan.id))).all()
    }
    for merged in payments:
        email = merged.email.strip().lower()
        user_id = user_ids.get(email)
        if user_id is None:
            report.problem(f"Legacy payment for {email!r}, who is not in the user export.")
            continue
        existing = await session.scalar(
            select(Payment.id).where(Payment.stripe_payment_intent_id == merged.stripe_payment_intent_id)
        )
        if existing is not None:
            continue
        plan_id = plans.get(merged.plan_code.lower())
        amount = merged.amount_pence
        if plan_id is not None and amount == 0:
            row = await session.scalar(select(Plan.amount_pence).where(Plan.id == plan_id))
            if row is not None:
                amount = int(row)
        session.add(
            Payment(
                user_id=user_id,
                plan_id=plan_id,
                stripe_payment_intent_id=merged.stripe_payment_intent_id,
                amount_total_pence=amount,
                currency="gbp",
                paid_at=merged.paid_at,
            )
        )
        report.payments_created += 1
    await session.flush()
    return report


async def load_legacy_referrals(
    session: AsyncSession,
    referrals: Sequence[MergedReferral],
    *,
    user_ids: dict[str, uuid.UUID],
) -> LoadReport:
    report = LoadReport()
    for merged in referrals:
        email = merged.email.strip().lower()
        user_id = user_ids.get(email)
        if user_id is None:
            report.problem(f"Referral for {email!r}, who is not in the user export.")
            continue
        taken = await session.scalar(select(Referral.id).where(Referral.code == merged.code))
        if taken is not None:
            continue
        session.add(
            Referral(
                referrer_user_id=user_id,
                code=merged.code,
                earned_pence=merged.earned_pence,
            )
        )
        report.referrals_created += 1
    await session.flush()
    return report
