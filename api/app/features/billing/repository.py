"""Storage for plans, payments and the webhook ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
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


async def seen_event_ids(session: AsyncSession, event_id: str) -> set[str]:
    """Only the one id matters, so this does not scan the table."""
    stmt = select(StripeEvent.event_id).where(StripeEvent.event_id == event_id)
    return set((await session.execute(stmt)).scalars())


async def record_event(
    session: AsyncSession, *, event_id: str, event_type: str, payload: dict[str, Any] | None
) -> StripeEvent:
    row = StripeEvent(event_id=event_id, event_type=event_type, payload=payload)
    session.add(row)
    await session.flush()
    return row


async def mark_event_processed(session: AsyncSession, *, event_id: str, at: datetime) -> None:
    await session.execute(update(StripeEvent).where(StripeEvent.event_id == event_id).values(processed_at=at))


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
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def payments_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Payment]:
    stmt = select(Payment).where(Payment.user_id == user_id).order_by(Payment.paid_at.desc())
    return list((await session.execute(stmt)).scalars())
