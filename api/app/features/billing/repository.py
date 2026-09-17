"""Storage for plans, payments and the webhook ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing.models import Payment, Plan, StripeEvent


async def active_plans(session: AsyncSession) -> list[Plan]:
    stmt = select(Plan).where(Plan.active.is_(True)).order_by(Plan.amount_pence)
    return list((await session.execute(stmt)).scalars())


async def create_plan(
    session: AsyncSession,
    *,
    code: str,
    stripe_price_id: str,
    amount_pence: int,
    duration_days: int,
    exam_code: str | None = None,
    currency: str = "gbp",
) -> Plan:
    row = Plan(
        code=code,
        stripe_price_id=stripe_price_id,
        amount_pence=amount_pence,
        duration_days=duration_days,
        exam_code=exam_code,
        currency=currency,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def processed_event_ids(session: AsyncSession, event_id: str) -> set[str]:
    """Only the one id matters, so this does not scan the table.

    Processed only: a delivery that was recorded but failed to apply is not
    "seen" for idempotency purposes, so Stripe's retry gets another go once
    whatever refused it (a missing account, a missing plan) has been fixed.
    """
    stmt = select(StripeEvent.event_id).where(
        StripeEvent.event_id == event_id, StripeEvent.processed_at.is_not(None)
    )
    return set((await session.execute(stmt)).scalars())


async def event_by_id(session: AsyncSession, event_id: str) -> StripeEvent | None:
    stmt = select(StripeEvent).where(StripeEvent.event_id == event_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def record_event(
    session: AsyncSession, *, event_id: str, event_type: str, payload: dict[str, Any] | None
) -> bool:
    """Write the ledger row. False if it already existed.

    `ON CONFLICT DO NOTHING` rather than check-then-insert: two deliveries of
    the same event in flight together used to race to the unique index and
    the loser answered Stripe with a 500.
    """
    stmt = (
        pg_insert(StripeEvent)
        .values(event_id=event_id, event_type=event_type, payload=payload)
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(StripeEvent.event_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def mark_event_processed(session: AsyncSession, *, event_id: str, at: datetime) -> None:
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
    row = Payment(
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
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def payments_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Payment]:
    stmt = select(Payment).where(Payment.user_id == user_id).order_by(Payment.paid_at.desc())
    return list((await session.execute(stmt)).scalars())


async def count_payments_for_users(session: AsyncSession, user_ids: list[uuid.UUID]) -> int:
    """How many payments these people have made. Zero for an empty list."""
    if not user_ids:
        return 0
    stmt = select(func.count(Payment.id)).where(Payment.user_id.in_(user_ids))
    return int((await session.execute(stmt)).scalar_one())


async def payment_by_receipt_id(session: AsyncSession, user_id: uuid.UUID, receipt_id: str) -> Payment | None:
    """One of this person's receipts, scoped to them.

    Scoped deliberately: a receipt id is short and printed on a document that
    gets forwarded, so it must not be a key anybody holding it can read.
    """
    stmt = select(Payment).where(Payment.user_id == user_id, Payment.receipt_id == receipt_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def plan_by_id(session: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    return (await session.execute(select(Plan).where(Plan.id == plan_id))).scalar_one_or_none()
