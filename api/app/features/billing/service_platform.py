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
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.identity.service import UserRef


async def _require_user(session: AsyncSession, user_id: uuid.UUID) -> UserRef:
    """The account a support read is scoped to, or raise `PayerNotFound` if it does not exist."""
    user = await identity.user_ref_by_id(session, user_id)
    if user is None:
        raise errors.PayerNotFound()
    return user


async def payments_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[PlatformPaymentRead]:
    """This person's payments, newest first, with the plan code each one bought resolved in."""
    await _require_user(session, user_id)
    payments = await repository.payments_for_user(session, user_id)
    plans = {payment.plan_id for payment in payments if payment.plan_id is not None}
    codes = {}
    for plan_id in plans:
        plan = await repository.plan_by_id(session, plan_id)
        codes[plan_id] = plan.code if plan else None
    revoked = await entitlements.revoked_ids(
        session, [payment.entitlement_id for payment in payments if payment.entitlement_id is not None]
    )
    return [
        _payment_read(
            payment,
            plan_code=codes.get(payment.plan_id) if payment.plan_id else None,
            access_revoked=payment.entitlement_id in revoked,
        )
        for payment in payments
    ]


async def payment_read(
    session: AsyncSession, payment: Payment, *, plan_code: str | None
) -> PlatformPaymentRead:
    """One payment as the console reads it, including whether its grant has been withdrawn."""
    revoked = payment.entitlement_id is not None and bool(
        await entitlements.revoked_ids(session, [payment.entitlement_id])
    )
    return _payment_read(payment, plan_code=plan_code, access_revoked=revoked)


async def list_events(
    session: AsyncSession, *, failed_only: bool, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[StripeEventRead], str | None]:
    """The webhook ledger, a page at a time; `failed_only` narrows it to the reconcile queue."""
    events, next_cursor = await repository.list_events(
        session, failed_only=failed_only, limit=limit, cursor=cursor
    )
    return [_event_read(event) for event in events], next_cursor


async def events_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[StripeEventRead]:
    """Every delivery that named this person's address, applied or not."""
    user = await _require_user(session, user_id)
    return [_event_read(event) for event in await repository.events_for_email(session, user.email)]


def _payment_read(payment: Payment, *, plan_code: str | None, access_revoked: bool) -> PlatformPaymentRead:
    """A payment row as the platform console's read model, with its plan code already resolved
    (a `Payment` row keeps only `plan_id`, an internal key support never sees)."""
    return PlatformPaymentRead(
        id=payment.id,
        user_id=payment.user_id,
        receipt_id=payment.receipt_id,
        stripe_payment_intent_id=payment.stripe_payment_intent_id,
        checkout_session_id=payment.checkout_session_id,
        amount_total_pence=payment.amount_total_pence,
        amount_tax_pence=payment.amount_tax_pence,
        currency=payment.currency,
        paid_at=payment.paid_at,
        plan_code=plan_code,
        plan_starts_at=payment.plan_starts_at,
        plan_ends_at=payment.plan_ends_at,
        entitlement_id=payment.entitlement_id,
        access_revoked=access_revoked,
        receipt_url=payment.receipt_url,
        customer_email=payment.customer_email,
    )


def _event_read(event: StripeEvent) -> StripeEventRead:
    """A ledger row as the platform console's read model, with the customer email and price it
    named pulled back out of the stored Stripe payload for display."""
    event_payload = ((event.payload or {}).get("data") or {}).get("object") or {}
    email = event_payload.get("customer_email") or (event_payload.get("customer_details") or {}).get("email")
    return StripeEventRead(
        event_id=event.event_id,
        event_type=event.event_type,
        received_at=event.received_at,
        processed_at=event.processed_at,
        failure=event.failure,
        customer_email=str(email).strip() if email else None,
        price_id=_price_id(event_payload) or None,
        payment_intent_id=str(event_payload.get("payment_intent") or "").strip() or None,
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
    """Each of these people's most recent purchase, for the account directory's "paid" facet."""
    latest_by_user = await repository.latest_payments(session, user_ids)
    return {
        user_id: PaymentFact(plan_code=code, paid_at=paid_at, plan_ends_at=ends_at)
        for user_id, (code, paid_at, ends_at) in latest_by_user.items()
    }
