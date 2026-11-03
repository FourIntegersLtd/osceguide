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

from app.features.billing import errors, repository, service_station_limit
from app.features.billing.models import Payment, StripeEvent
from app.features.billing.schemas import (
    PlatformAccessGrantRead,
    PlatformExamAccessRead,
    PlatformPaymentRead,
    StripeEventRead,
)
from app.features.billing.service import _price_id
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.identity.service import UserRef
from app.features.stations import service_plan_window


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


async def access_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> list[PlatformExamAccessRead]:
    """Per exam this person has ever held a grant for: the station limit that applies now, the
    stations sat, why, and the grants behind it. Reuses the learner's own limit rule, so staff see
    exactly what the person sees.

    Exams are grouped by the grants' own exam id, so a retired, draft or institution-owned exam
    never fails the read; a grant whose exam is gone altogether has no code and is left out.
    """
    await _require_user(session, user_id)
    grants = await entitlements.list_for_user(session, user_id, now=now)
    plan_codes_by_id = {plan.id: plan.code for plan in await repository.all_plans(session)}
    plan_code_by_entitlement: dict[uuid.UUID, str] = {}
    payment_by_entitlement: dict[uuid.UUID, Payment] = {}
    for payment in await repository.payments_for_user(session, user_id):
        plan_code = plan_codes_by_id.get(payment.plan_id) if payment.plan_id else None
        if plan_code is not None and payment.entitlement_id is not None:
            plan_code_by_entitlement[payment.entitlement_id] = plan_code
            payment_by_entitlement[payment.entitlement_id] = payment
    result: list[PlatformExamAccessRead] = []
    for exam_id in dict.fromkeys(grant.exam_id for grant in grants):
        exam_grants = [grant for grant in grants if grant.exam_id == exam_id]
        exam_code = exam_grants[0].exam_code
        if not exam_code:
            continue
        stations_sat, station_limit = await service_plan_window.plan_usage(
            session, user_id=user_id, exam_id=exam_id, exam_code=exam_code, now=now
        )
        other_live = [grant for grant in exam_grants if grant.live and grant.source != "purchase"]
        _, deciding_plan_code = await service_station_limit.station_limit_and_plan_code(
            session, user_id=user_id, exam_code=exam_code, now=now, started_only=True
        )
        if other_live:
            reason = f"unlimited:{other_live[0].source}"
        elif deciding_plan_code is not None:
            reason = f"plan:{deciding_plan_code}"
        else:
            reason = "no_access"
        result.append(
            PlatformExamAccessRead(
                exam_code=exam_code,
                station_limit=station_limit,
                stations_sat=stations_sat,
                limit_reason=reason,
                grants=[
                    PlatformAccessGrantRead(
                        entitlement_id=grant.id,
                        source=grant.source,
                        plan_code=plan_code_by_entitlement.get(grant.id),
                        payment_id=_payment_field(payment_by_entitlement, grant.id, "id"),
                        payment_reference=_payment_field(
                            payment_by_entitlement, grant.id, "stripe_payment_intent_id"
                        ),
                        starts_at=grant.starts_at,
                        ends_at=grant.ends_at,
                        revoked_at=grant.revoked_at,
                        live=grant.live,
                    )
                    for grant in exam_grants
                ],
            )
        )
    return result


def _payment_field(payments: dict[uuid.UUID, Payment], entitlement_id: uuid.UUID, field: str) -> Any:
    """One field of the payment that bought this grant, or `None` when it was not bought."""
    payment = payments.get(entitlement_id)
    return getattr(payment, field) if payment is not None else None


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


async def paying_ids_among(session: AsyncSession, user_ids: Collection[uuid.UUID]) -> set[uuid.UUID]:
    """Of these people, the ones who have really paid (more than 0 pence) at least once."""
    return await repository.paying_user_ids_among(session, user_ids)


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
