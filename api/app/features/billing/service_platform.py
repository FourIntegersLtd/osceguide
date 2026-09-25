"""Payments and the webhook ledger, as the people who answer support see them.

The refund path, the manual grant and the replay live in `service_platform_actions`; these are
the reads that tell support which of them a case needs.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import errors, repository
from app.features.billing.models import Payment, StripeEvent
from app.features.billing.schemas import PlatformPaymentRead, StripeEventRead
from app.features.billing.service import _price_id
from app.features.identity import service as identity
from app.features.identity.service import UserRef


async def _require_user(session: AsyncSession, user_id: uuid.UUID) -> UserRef:
    user = await identity.user_ref_by_id(session, user_id)
    if user is None:
        raise errors.PayerNotFound()
    return user


async def payments_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[PlatformPaymentRead]:
    await _require_user(session, user_id)
    rows = await repository.payments_for_user(session, user_id)
    plans = {row.plan_id for row in rows if row.plan_id is not None}
    codes = {}
    for plan_id in plans:
        plan = await repository.plan_by_id(session, plan_id)
        codes[plan_id] = plan.code if plan else None
    return [_payment_read(row, plan_code=codes.get(row.plan_id) if row.plan_id else None) for row in rows]


async def list_events(
    session: AsyncSession, *, failed_only: bool, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[StripeEventRead], str | None]:
    rows, next_cursor = await repository.list_events(
        session, failed_only=failed_only, limit=limit, cursor=cursor
    )
    return [_event_read(row) for row in rows], next_cursor


async def events_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[StripeEventRead]:
    """Every delivery that named this person's address, applied or not."""
    user = await _require_user(session, user_id)
    return [_event_read(row) for row in await repository.events_for_email(session, user.email)]


def _payment_read(row: Payment, *, plan_code: str | None) -> PlatformPaymentRead:
    return PlatformPaymentRead(
        id=row.id,
        user_id=row.user_id,
        receipt_id=row.receipt_id,
        stripe_payment_intent_id=row.stripe_payment_intent_id,
        checkout_session_id=row.checkout_session_id,
        amount_total_pence=row.amount_total_pence,
        amount_tax_pence=row.amount_tax_pence,
        currency=row.currency,
        paid_at=row.paid_at,
        plan_code=plan_code,
        plan_starts_at=row.plan_starts_at,
        plan_ends_at=row.plan_ends_at,
        entitlement_id=row.entitlement_id,
        receipt_url=row.receipt_url,
        customer_email=row.customer_email,
    )


def _event_read(row: StripeEvent) -> StripeEventRead:
    payload = ((row.payload or {}).get("data") or {}).get("object") or {}
    email = payload.get("customer_email") or (payload.get("customer_details") or {}).get("email")
    return StripeEventRead(
        event_id=row.event_id,
        event_type=row.event_type,
        received_at=row.received_at,
        processed_at=row.processed_at,
        failure=row.failure,
        customer_email=str(email).strip() if email else None,
        price_id=_price_id(payload) or None,
        payment_intent_id=str(payload.get("payment_intent") or "").strip() or None,
    )


# --- What the account directory knows about paying, for many people at once.


@dataclass(frozen=True)
class PaymentFact:
    """The last thing somebody bought."""

    plan_code: str | None
    paid_at: datetime
    plan_ends_at: datetime | None


async def payer_ids(session: AsyncSession) -> set[uuid.UUID]:
    """Everyone who has ever paid — the directory's "paid" facet."""
    return await repository.payer_user_ids(session)


async def payer_ids_on_plan(session: AsyncSession, plan_code: str) -> set[uuid.UUID]:
    return await repository.payer_user_ids_on_plan(session, plan_code)


async def latest_payment_by_user(
    session: AsyncSession, user_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, PaymentFact]:
    rows = await repository.latest_payments(session, user_ids)
    return {
        user_id: PaymentFact(plan_code=code, paid_at=paid_at, plan_ends_at=ends_at)
        for user_id, (code, paid_at, ends_at) in rows.items()
    }
