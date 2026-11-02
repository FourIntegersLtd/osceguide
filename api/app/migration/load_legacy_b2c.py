"""Payments and referrals from B2C user documents."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan
from app.features.growth.models import Referral
from app.migration.link_payments import link_legacy_payments
from app.migration.report import LoadReport
from app.migration.users import MergedLegacyPayment, MergedReferral

LEGACY_CONSUMER_PROVIDER = "consumer"


async def load_legacy_payments(
    session: AsyncSession,
    payments: Sequence[MergedLegacyPayment],
    *,
    user_ids: dict[str, uuid.UUID],
) -> LoadReport:
    """Load legacy Stripe payments, matched to platform users by email.

    Skips a payment already recorded by its `stripe_payment_intent_id`, except that one
    left with no plan and 0p is given its plan and price. A payment for
    an email not in `user_ids` (the user step's output) is reported, not guessed at.
    """
    report = LoadReport()
    plan_rows = (await session.execute(select(Plan.code, Plan.id, Plan.amount_pence))).all()
    plans = {str(code).lower(): plan_id for code, plan_id, _ in plan_rows}
    plan_amounts = {plan_id: int(amount) for _, plan_id, amount in plan_rows}
    for merged in payments:
        email = merged.email.strip().lower()
        user_id = user_ids.get(email)
        if user_id is None:
            report.problem(f"Legacy payment for {email!r}, who is not in the user export.")
            continue
        plan_id = plans.get(merged.plan_code.lower())
        if plan_id is None:
            report.problem(
                f"Legacy payment {merged.stripe_payment_intent_id!r} for {email!r}: "
                f"no platform plan {merged.plan_code!r}; imported without a plan."
            )
        plan_amount_pence = plan_amounts.get(plan_id) if plan_id is not None else None
        existing = await session.scalar(
            select(Payment).where(Payment.stripe_payment_intent_id == merged.stripe_payment_intent_id)
        )
        if existing is not None:
            # An earlier run that could not resolve the plan left plan NULL and 0p; repair only that.
            if (
                existing.plan_id is None
                and existing.amount_total_pence == 0
                and plan_amount_pence is not None
            ):
                existing.plan_id = plan_id
                existing.amount_total_pence = plan_amount_pence
                report.payments_repaired += 1
            continue
        amount = merged.amount_pence
        if amount == 0 and plan_amount_pence is not None:
            amount = plan_amount_pence
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
    # Tie each payment to the grant it bought, or no station limit or refund can find it.
    link_report = await link_legacy_payments(session, user_ids=set(user_ids.values()))
    for line in link_report.unresolved:
        report.problem(line)
    return report


async def load_legacy_referrals(
    session: AsyncSession,
    referrals: Sequence[MergedReferral],
    *,
    user_ids: dict[str, uuid.UUID],
) -> LoadReport:
    """Load legacy referral codes and earnings, matched to platform users by email.

    Skips a code already present. A referral for an email not in `user_ids` is reported.
    """
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
