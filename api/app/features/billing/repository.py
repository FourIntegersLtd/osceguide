"""Storage for plans, payments and the webhook ledger."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.billing.models import Payment, Plan, StripeEvent


async def active_plans(session: AsyncSession) -> list[Plan]:
    """Every plan on sale, cheapest first."""
    stmt = select(Plan).where(Plan.active.is_(True)).order_by(Plan.amount_pence)
    return list((await session.execute(stmt)).scalars())


async def all_plans(session: AsyncSession) -> list[Plan]:
    """Every plan ever priced, on sale or retired, by exam and then cheapest first.

    What the webhook resolves a price against: a plan retired while a customer sat on its
    checkout page must still grant what they paid for.
    """
    stmt = select(Plan).order_by(Plan.exam_code, Plan.amount_pence, Plan.code)
    return list((await session.execute(stmt)).scalars())


async def any_plan_by_code(session: AsyncSession, code: str) -> Plan | None:
    """The plan with this code whether or not it is on sale, for staff managing it."""
    return (await session.execute(select(Plan).where(Plan.code == code))).scalar_one_or_none()


async def set_plans_active(session: AsyncSession, codes: Collection[str], *, active: bool) -> None:
    """Put these plans on sale or take them off it. Nothing else about a plan ever changes."""
    await session.execute(update(Plan).where(Plan.code.in_(list(codes))).values(active=active))


async def create_plan(
    session: AsyncSession,
    *,
    code: str,
    stripe_price_id: str,
    amount_pence: int,
    duration_days: int,
    exam_code: str,
    currency: str = "gbp",
) -> Plan:
    """Insert a new plan row for a Stripe price. Staff pricing and seeding; no customer path."""
    plan = Plan(
        code=code,
        stripe_price_id=stripe_price_id,
        amount_pence=amount_pence,
        duration_days=duration_days,
        exam_code=exam_code,
        currency=currency,
    )
    session.add(plan)
    await session.flush()
    await session.refresh(plan)
    return plan


async def processed_event_ids(session: AsyncSession, event_id: str) -> set[str]:
    """Processed only: a delivery recorded but failed to apply is not "seen" for idempotency,
    so Stripe's retry gets another go once whatever refused it has been fixed."""
    stmt = select(StripeEvent.event_id).where(
        StripeEvent.event_id == event_id, StripeEvent.processed_at.is_not(None)
    )
    return set((await session.execute(stmt)).scalars())


async def event_by_id(session: AsyncSession, event_id: str) -> StripeEvent | None:
    """The ledger row for one Stripe event id, or `None` if it was never recorded."""
    stmt = select(StripeEvent).where(StripeEvent.event_id == event_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def record_event(
    session: AsyncSession, *, event_id: str, event_type: str, event_payload: dict[str, Any] | None
) -> bool:
    """Write the ledger row. False if it already existed.

    `ON CONFLICT DO NOTHING` rather than check-then-insert: two deliveries of the same event in
    flight together used to race the unique index and the loser answered Stripe with a 500.
    """
    stmt = (
        pg_insert(StripeEvent)
        .values(event_id=event_id, event_type=event_type, payload=event_payload)
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(StripeEvent.event_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def mark_event_processed(session: AsyncSession, *, event_id: str, at: datetime) -> None:
    """Record that a delivery was applied, or acknowledged and deliberately ignored, and clear
    any earlier failure now that it has gone through."""
    await session.execute(
        update(StripeEvent).where(StripeEvent.event_id == event_id).values(processed_at=at, failure=None)
    )


async def mark_event_failed(session: AsyncSession, *, event_id: str, reason: str) -> None:
    await session.execute(update(StripeEvent).where(StripeEvent.event_id == event_id).values(failure=reason))


async def record_payment(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    plan_id: uuid.UUID | None,
    stripe_payment_intent_id: str,
    checkout_session_id: str | None,
    amount_total_pence: int,
    currency: str,
    receipt_url: str | None,
    paid_at: datetime,
    entitlement_id: uuid.UUID | None,
    receipt_id: str | None = None,
    customer_email: str | None = None,
    customer_name: str | None = None,
    amount_tax_pence: int = 0,
    plan_starts_at: datetime | None = None,
    plan_ends_at: datetime | None = None,
) -> Payment:
    """Insert the payment row that records one settled purchase."""
    payment = Payment(
        user_id=user_id,
        plan_id=plan_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        checkout_session_id=checkout_session_id,
        amount_total_pence=amount_total_pence,
        currency=currency,
        receipt_url=receipt_url,
        paid_at=paid_at,
        entitlement_id=entitlement_id,
        receipt_id=receipt_id,
        customer_email=customer_email,
        customer_name=customer_name,
        amount_tax_pence=amount_tax_pence,
        plan_starts_at=plan_starts_at,
        plan_ends_at=plan_ends_at,
    )
    session.add(payment)
    await session.flush()
    await session.refresh(payment)
    return payment


async def payments_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, checkout_session_id: str | None = None
) -> list[Payment]:
    """This person's payments, most recent first; only one Stripe checkout session's when given."""
    stmt = select(Payment).where(Payment.user_id == user_id).order_by(Payment.paid_at.desc())
    if checkout_session_id is not None:
        stmt = stmt.where(Payment.checkout_session_id == checkout_session_id)
    return list((await session.execute(stmt)).scalars())


async def payments_page(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    checkout_session_id: str | None = None,
) -> tuple[list[Payment], str | None]:
    """One page of this person's payments that have a receipt, newest first, with the next cursor.

    Payments from before receipts existed have no receipt id and are not listed.
    """
    stmt = select(Payment).where(Payment.user_id == user_id, Payment.receipt_id.is_not(None))
    if checkout_session_id is not None:
        stmt = stmt.where(Payment.checkout_session_id == checkout_session_id)
    return await keyset_page(
        session, stmt, sort_col=Payment.paid_at, id_col=Payment.id, limit=limit, cursor=cursor
    )


async def count_payments_for_users(session: AsyncSession, user_ids: list[uuid.UUID]) -> int:
    """How many payments these people have made. Zero for an empty list."""
    if not user_ids:
        return 0
    stmt = select(func.count(Payment.id)).where(Payment.user_id.in_(user_ids))
    return int((await session.execute(stmt)).scalar_one())


async def revenue_for_users(
    session: AsyncSession, user_ids: list[uuid.UUID], *, paid_from: datetime, paid_before: datetime
) -> int:
    """Pence these people paid in a window, gross. Zero for an empty list."""
    if not user_ids:
        return 0
    stmt = select(func.coalesce(func.sum(Payment.amount_total_pence), 0)).where(
        Payment.user_id.in_(user_ids), Payment.paid_at >= paid_from, Payment.paid_at < paid_before
    )
    return int((await session.execute(stmt)).scalar_one())


async def payment_by_receipt_id(session: AsyncSession, user_id: uuid.UUID, receipt_id: str) -> Payment | None:
    """One of this person's receipts, scoped to them: a receipt id is short and printed on a
    document that gets forwarded, so it must not be a key anybody holding it can read."""
    stmt = select(Payment).where(Payment.user_id == user_id, Payment.receipt_id == receipt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def plan_by_code(session: AsyncSession, code: str) -> Plan | None:
    """The plan a customer names when they start a checkout. By code rather than by price id:
    the price id is Stripe's and changes when a price does."""
    stmt = select(Plan).where(Plan.code == code, Plan.active.is_(True))
    return (await session.execute(stmt)).scalar_one_or_none()


async def plan_by_id(session: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    return (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()


async def list_events(
    session: AsyncSession, *, failed_only: bool, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[StripeEvent], str | None]:
    """The webhook ledger, newest first. `failed_only` is the reconcile queue:
    deliveries recorded but never applied, refused or not."""
    stmt = select(StripeEvent)
    if failed_only:
        stmt = stmt.where(StripeEvent.processed_at.is_(None))
    return await keyset_page(
        session, stmt, sort_col=StripeEvent.received_at, id_col=StripeEvent.id, limit=limit, cursor=cursor
    )


def _payload_email(field: str) -> Any:
    """A case-folded SQL expression reading one email-shaped field out of the stored JSON
    payload, for matching an address regardless of how Stripe capitalised it."""
    payload_column = StripeEvent.payload
    return func.lower(payload_column["data"]["object"][field].astext)


async def events_for_email(session: AsyncSession, email: str) -> list[StripeEvent]:
    """Every delivery naming this address, newest first — read from the payload, which is why
    it is kept: a payment for an address with no account at the time is what support asks about."""
    wanted = email.strip().lower()
    details = func.lower(StripeEvent.payload["data"]["object"]["customer_details"]["email"].astext)
    stmt = (
        select(StripeEvent)
        .where(or_(_payload_email("customer_email") == wanted, details == wanted))
        .order_by(StripeEvent.received_at.desc())
    )
    return list((await session.execute(stmt)).scalars())


async def payment_by_id(session: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return (await session.execute(select(Payment).where(Payment.id == payment_id))).scalar_one_or_none()


async def lock_payment(session: AsyncSession, payment_id: uuid.UUID) -> None:
    """Hold this payment's row until the transaction ends, so two withdrawals of it queue up."""
    await session.execute(select(Payment.id).where(Payment.id == payment_id).with_for_update())


async def payment_by_intent(session: AsyncSession, intent_id: str) -> Payment | None:
    """The payment recorded against a Stripe payment intent (or a manual reference), if any."""
    stmt = select(Payment).where(Payment.stripe_payment_intent_id == intent_id)
    return (await session.execute(stmt)).scalar_one_or_none()


# --- Storage reads the platform console asks about many payers at once.


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


async def payer_user_ids_among(
    session: AsyncSession, user_ids: Collection[uuid.UUID], *, paid_from: datetime, paid_before: datetime
) -> set[uuid.UUID]:
    """Of these people, the ones with at least one payment in the window. Empty for an empty list.

    For a partner breakdown: which of the users it was credited with acquiring
    paid within the range being read (b2c's `_aggregate_payments` payer set),
    without asking about every payer on the platform.
    """
    if not user_ids:
        return set()
    stmt = (
        select(Payment.user_id)
        .where(
            Payment.user_id.in_(list(user_ids)), Payment.paid_at >= paid_from, Payment.paid_at < paid_before
        )
        .distinct()
    )
    return set((await session.execute(stmt)).scalars())


async def revenue_breakdown_for_users(
    session: AsyncSession, user_ids: Collection[uuid.UUID], *, paid_from: datetime, paid_before: datetime
) -> list[tuple[str | None, int, int]]:
    """What these people paid in a window, split by the plan they bought.

    Each row is `(plan code, payment count, gross revenue pence)`; a payment
    whose plan was since deleted (`plan_id` gone `SET NULL`) groups under a
    `None` code, which the caller reads as "unknown". Empty for an empty list
    of users.
    """
    if not user_ids:
        return []
    stmt = (
        select(Plan.code, func.count(Payment.id), func.coalesce(func.sum(Payment.amount_total_pence), 0))
        .select_from(Payment)
        .outerjoin(Plan, Plan.id == Payment.plan_id)
        .where(
            Payment.user_id.in_(list(user_ids)),
            Payment.paid_at >= paid_from,
            Payment.paid_at < paid_before,
        )
        .group_by(Plan.code)
    )
    return [(code, int(count), int(gross)) for code, count, gross in (await session.execute(stmt)).all()]


async def revenue_over_time_for_users(
    session: AsyncSession,
    user_ids: Collection[uuid.UUID],
    *,
    paid_from: datetime,
    paid_before: datetime,
    bucket: str,
) -> list[tuple[datetime, int, int]]:
    """Revenue from these people, grouped into `date_trunc(bucket, paid_at)` buckets.

    Only the buckets with at least one payment; the caller gap-fills the empty
    ones so a chart's x-axis is continuous. Empty for an empty list of users.
    """
    if not user_ids:
        return []
    period = func.date_trunc(bucket, Payment.paid_at).label("period")
    stmt = (
        select(period, func.count(Payment.id), func.coalesce(func.sum(Payment.amount_total_pence), 0))
        .where(
            Payment.user_id.in_(list(user_ids)),
            Payment.paid_at >= paid_from,
            Payment.paid_at < paid_before,
        )
        .group_by(period)
        .order_by(period)
    )
    rows = (await session.execute(stmt)).all()
    return [(period_start, int(count), int(gross)) for period_start, count, gross in rows]


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
