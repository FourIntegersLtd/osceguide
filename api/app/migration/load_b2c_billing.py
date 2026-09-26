"""Copying consumer payments, referral redemptions and partner attribution.

- **Payments** come from the `*_payments` collections, which carry the receipt,
  checkout session and tax the user-document import (`legacy_payment_for`) never
  saw. A payment that import already made is matched on its payment intent and
  only has its empty columns filled in.
- **Referrals** in Firestore are one document per redemption of a reusable code.
  The platform keeps one single-use code per row, so each redemption becomes a
  redeemed row under `<CODE>-<first six of the redemption id>`, which keeps the
  original code readable and cannot collide with a code anybody can type.
- **Partner arrivals and reporters** copy as they are; demo rows are already
  dropped by `b2c_firestore.stream`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan
from app.features.growth.models import PartnerArrival, PartnerReporter, Referral
from app.migration.b2c_lookups import Lookups, StepReport
from app.migration.legacy_ids import legacy_row_id
from app.migration.users import UnknownLegacyProduct, exam_for_product, parse_timestamp

_PLAN_SUFFIX = {"one_month": "1m", "three_month": "3m", "six_month": "6m"}
_FILL = (
    "checkout_session_id",
    "receipt_url",
    "customer_email",
    "customer_name",
    "plan_starts_at",
    "plan_ends_at",
)


def _payment_values(doc: dict[str, Any]) -> dict[str, Any]:
    """The receipt/checkout/plan-window fields a payment document carries, for insert or backfill."""
    return {
        "checkout_session_id": (doc.get("checkout_session_id") or None),
        "receipt_url": (doc.get("stripe_receipt_url") or None),
        "customer_email": (doc.get("customer_email") or None),
        "customer_name": (str(doc.get("customer_name") or "")[:200] or None),
        "plan_starts_at": parse_timestamp(doc.get("plan_start_date")),
        "plan_ends_at": parse_timestamp(doc.get("plan_end_date")),
    }


async def load_payments(
    session: AsyncSession, documents: Sequence[dict[str, Any]], lookups: Lookups
) -> StepReport:
    """Load legacy `*_payments` documents into `payments`.

    A payment `import_b2c_users` already created (matched on Stripe payment
    intent) only has its empty receipt/checkout/plan-window columns filled in;
    a payment seen for the first time here is inserted in full.
    """
    report = StepReport()
    plans = {
        str(plan_code).lower(): plan_id
        for plan_code, plan_id in (await session.execute(select(Plan.code, Plan.id))).all()
    }
    receipts = set(
        (await session.scalars(select(Payment.receipt_id).where(Payment.receipt_id.isnot(None)))).all()
    )
    for doc in documents:
        label = f"payment {doc.get('_collection')}/{doc.get('id')}"
        intent = str(doc.get("payment_intent_id") or "").strip()
        paid_at = parse_timestamp(doc.get("paid_at")) or parse_timestamp(doc.get("created_at"))
        if not intent or paid_at is None:
            report.problem(f"{label}: no payment intent or payment time")
            continue
        payment_field_values = _payment_values(doc)
        receipt = str(doc.get("receipt_id") or "").strip() or None
        existing = await session.scalar(select(Payment).where(Payment.stripe_payment_intent_id == intent))
        if existing is not None:
            filled = [
                field
                for field in _FILL
                if getattr(existing, field) is None and payment_field_values[field] is not None
            ]
            for key in filled:
                setattr(existing, key, payment_field_values[key])
            if existing.receipt_id is None and receipt and receipt not in receipts:
                existing.receipt_id = receipt
                receipts.add(receipt)
                filled.append("receipt_id")
            report.count("payments filled in" if filled else "payments already there")
            continue
        user_id = lookups.user(doc.get("user_id")) or lookups.user_by_email(doc.get("customer_email"))
        if user_id is None:
            report.problem(
                f"{label}: no platform user for {doc.get('user_id')!r} / {doc.get('customer_email')!r}"
            )
            continue
        exam = str(doc.get("app_type") or "").lower()
        suffix = _PLAN_SUFFIX.get(str(doc.get("plan_type") or ""), "")
        session.add(
            Payment(
                id=legacy_row_id(f"{exam}:payment:{doc.get('id')}"),
                user_id=user_id,
                plan_id=plans.get(f"{exam}_{suffix}") or plans.get(f"all_{suffix}"),
                stripe_payment_intent_id=intent,
                amount_total_pence=int(doc.get("amount_total_pence") or 0),
                amount_tax_pence=int(doc.get("amount_tax_pence") or 0),
                currency=str(doc.get("currency") or "gbp")[:3],
                receipt_id=receipt if receipt and receipt not in receipts else None,
                paid_at=paid_at,
                **payment_field_values,
            )
        )
        if receipt:
            receipts.add(receipt)
        report.count("payments created")
    await session.flush()
    return report


async def load_referrals(
    session: AsyncSession, documents: Sequence[dict[str, Any]], lookups: Lookups
) -> StepReport:
    """Load legacy referral redemptions into `referrals`, one row per redemption of a reusable code.

    The platform's `referrals` table is single-use per row, so each redemption
    becomes `<CODE>-<first six of the redemption id>`: readable, and never
    collides with a code someone might type themselves.
    """
    report = StepReport()
    for doc in documents:
        redemption = str(doc.get("referral_id") or doc.get("id") or "")
        label = f"referral {doc.get('_collection')}/{redemption}"
        try:
            exam = exam_for_product(doc.get("app_type"))
        except UnknownLegacyProduct as exc:
            report.problem(f"{label}: {exc}")
            continue
        row_id = legacy_row_id(f"{exam}:referral:{redemption}")
        if await session.get(Referral, row_id) is not None:
            report.count("referrals already there")
            continue
        code = str(doc.get("referral_code_used") or "").strip().upper()
        referrer = lookups.user(doc.get("referrer_id"))
        if not code or referrer is None:
            report.problem(f"{label}: no code, or no platform user for referrer {doc.get('referrer_id')!r}")
            continue
        redeemed_at = parse_timestamp(doc.get("created_at"))
        session.add(
            Referral(
                id=row_id,
                referrer_user_id=referrer,
                code=f"{code}-{redemption.replace('-', '')[:6]}".upper()[:32],
                referred_user_id=lookups.user_by_email(doc.get("referee_email")),
                redeemed_at=redeemed_at,
                earned_pence=int(doc.get("amount_earned") or 0),
                payout_status=str(doc.get("payout_status") or "unpaid")[:16],
                **({"created_at": redeemed_at} if redeemed_at else {}),
            )
        )
        report.count("referral redemptions created")
    await session.flush()
    return report


def _arrival(doc: dict[str, Any]) -> PartnerArrival:
    """Transform a legacy partner-arrival document into a `PartnerArrival` row, UTM tags from its path."""
    path = str(doc.get("landing_path") or "")
    query = {
        query_key: query_values[0]
        for query_key, query_values in parse_qs(urlparse(path).query).items()
        if query_values
    }
    utm = {
        utm_field: doc.get(f"utm_{utm_field}") or query.get(f"utm_{utm_field}")
        for utm_field in ("source", "medium", "campaign")
    }
    landed = parse_timestamp(doc.get("landed_at")) or parse_timestamp(doc.get("created_at"))
    return PartnerArrival(
        id=legacy_row_id(f"partner_arrival:{doc.get('arrival_id') or doc.get('id')}"),
        partner=str(doc.get("partner") or "")[:32],
        exam_code=(str(doc.get("exam") or "")[:32] or None),
        visitor_key=str(doc.get("visitor_key") or doc.get("id"))[:64],
        ref_id=(query.get("ref_id") or None),
        landing_path=path[:300] or None,
        utm={utm_field: utm_value for utm_field, utm_value in utm.items() if utm_value} or None,
        **({"landed_at": landed} if landed else {}),
    )


async def load_partners(
    session: AsyncSession, arrivals: Sequence[dict], reporters: Sequence[dict]
) -> StepReport:
    """Load legacy partner arrivals and reporters as they are; demo rows are already dropped upstream."""
    report = StepReport()
    for doc in arrivals:
        arrival = _arrival(doc)
        if not arrival.partner or await session.get(PartnerArrival, arrival.id) is not None:
            report.count(
                "partner arrivals already there" if arrival.partner else "partner arrivals with no partner"
            )
            continue
        session.add(arrival)
        report.count("partner arrivals created")
    for doc in reporters:
        partner, email = str(doc.get("partner") or ""), str(doc.get("email") or "").strip().lower()
        taken = await session.scalar(
            select(PartnerReporter.id).where(
                PartnerReporter.partner == partner, PartnerReporter.email == email
            )
        )
        if not partner or not email or taken is not None:
            report.count("partner reporters already there or incomplete")
            continue
        session.add(
            PartnerReporter(
                id=legacy_row_id(f"partner_reporter:{doc.get('id')}"), partner=partner, email=email
            )
        )
        report.count("partner reporters created")
    await session.flush()
    return report
