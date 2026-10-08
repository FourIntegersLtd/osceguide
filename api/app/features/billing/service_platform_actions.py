"""What support may do about a payment, once `service_platform` has said what happened.

Four actions: replay a delivery that did not go through, record a payment that never went
through Stripe, mark a refund (See ADR 0012), and issue one in Stripe first (`stripe_refund`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError
from app.core.ports import CheckoutRefused, CheckoutSessions, CheckoutUnavailable
from app.core.settings import SettingsDep
from app.features.billing import domain, errors, repository, service, service_platform, service_settlement
from app.features.billing.models import Payment, StripeEvent
from app.features.billing.schemas import PlatformPaymentRead
from app.features.entitlements import service as entitlement_grants
from app.features.entitlements import service_platform as entitlements
from app.features.identity import service as identity
from app.features.tenancy import service_audit


def get_stripe_refunds(settings: SettingsDep) -> CheckoutSessions:
    """The Stripe adapter for refunds, as the router's dependency. Overridden in tests."""
    from app.features.billing.checkout import build_checkout

    try:
        return build_checkout(settings)
    except CheckoutUnavailable as exc:
        raise errors.StripeRefundFailed() from exc


async def replay_event(
    session: AsyncSession, event_id: str, *, actor: Principal, now: datetime
) -> dict[str, str]:
    """Apply a recorded delivery again. `handle_event` is already idempotent — an applied event
    answers `already_applied` — so this cannot grant twice."""
    event = await repository.event_by_id(session, event_id)
    if event is None:
        raise errors.BillingEventNotFound()
    try:
        outcome = await service.handle_event(session, event=dict(event.payload or {}), now=now)
    except AppError as exc:
        await _audit_replay(session, actor, event_id, outcome=exc.code)
        raise
    await _audit_replay(session, actor, event_id, outcome=outcome["status"])
    return outcome


async def _audit_replay(session: AsyncSession, actor: Principal, event_id: str, *, outcome: str) -> None:
    """Log that support replayed a delivery and what happened, whether it succeeded or failed
    again with the same or a different cause."""
    await service_audit.record(
        session,
        actor=actor,
        action="billing.event_replayed",
        target_type="stripe_event",
        target_id=event_id,
        summary=outcome,
        meta={"outcome": outcome},
    )


async def record_manual_payment(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    plan_code: str,
    intent_id: str | None,
    amount_total_pence: int | None,
    paid_at: datetime | None,
    note: str,
    actor: Principal,
    now: datetime,
) -> PlatformPaymentRead:
    """Record a payment that did not come through Stripe, and grant what it bought.

    The same steps a checkout takes, so a sponsor's seat is a real purchase and not an admin
    grant with a story. Idempotent on the reference: recording the same intent twice is a
    conflict, never a second grant.
    """
    user = await identity.user_ref_by_id(session, user_id)
    if user is None:
        raise errors.PayerNotFound()
    plan_row = await repository.plan_by_code(session, plan_code)
    if plan_row is None:
        raise errors.PlanNotAvailable()
    reference = (intent_id or "").strip() or f"manual:{uuid.uuid4()}"
    if await repository.payment_by_intent(session, reference) is not None:
        raise errors.PaymentAlreadyRecorded()
    payment = await service_settlement.settle_payment(
        session,
        user=user,
        plan_row=plan_row,
        intent_id=reference,
        checkout_session_id=None,
        amount_total=plan_row.amount_pence if amount_total_pence is None else amount_total_pence,
        amount_tax=0,
        currency=plan_row.currency,
        receipt_url=None,
        customer_name=user.name,
        email=user.email,
        now=paid_at or now,
    )
    await service_audit.record(
        session,
        actor=actor,
        action="billing.payment_recorded_manually",
        target_type="payment",
        target_id=str(payment.id),
        summary=f"{plan_code} for {user.email}: {note}",
        meta={"user_id": str(user_id), "plan_code": plan_code, "reference": reference, "note": note},
    )
    return await service_platform.payment_read(session, payment, plan_code=plan_row.code)


async def refund(
    session: AsyncSession, payment_id: uuid.UUID, *, reason: str, actor: Principal, now: datetime
) -> PlatformPaymentRead:
    """Record that a payment was refunded: the access it bought is withdrawn. The payment row
    stays, its `entitlement_id` still pointing at the revoked grant. Twice is once: a repeat
    withdraws nothing and writes no audit row."""
    payment = await repository.payment_by_id(session, payment_id)
    if payment is None:
        raise errors.PaymentNotFound()

    async def revoke(entitlement_id: uuid.UUID) -> None:
        await entitlements.revoke(session, entitlement_id, reason=f"refund: {reason}", actor=actor, now=now)

    if await service_settlement.withdraw_payment(session, payment, revoke=revoke, now=now):
        await service_audit.record(
            session,
            actor=actor,
            action="billing.refund_recorded",
            target_type="payment",
            target_id=str(payment_id),
            summary=reason,
            meta={
                "user_id": str(payment.user_id),
                "reason": reason,
                "entitlement_id": str(payment.entitlement_id),
            },
        )
    plan = await repository.plan_by_id(session, payment.plan_id) if payment.plan_id else None
    return await service_platform.payment_read(session, payment, plan_code=plan.code if plan else None)


async def stripe_refund(
    session: AsyncSession,
    payment_id: uuid.UUID,
    *,
    reason: str,
    stripe: CheckoutSessions,
    actor: Principal,
    now: datetime,
) -> PlatformPaymentRead:
    """Refund the whole payment in Stripe, then withdraw what it bought (`refund`).

    Stripe first: if it refuses, nothing is withdrawn and the person keeps what they paid for. The
    idempotency key is the payment and the amount, so a double click or a retry after a lost answer
    is one refund. The `charge.refunded` webhook that follows finds the access already withdrawn.
    """
    payment = await repository.payment_by_id(session, payment_id)
    if payment is None:
        raise errors.PaymentNotFound()
    if not payment.stripe_payment_intent_id.startswith("pi_"):
        raise errors.NotAStripePayment()
    # Held until the transaction ends: a second click queues here and then finds the first's
    # withdrawal, instead of asking Stripe for a second refund.
    await repository.lock_payment(session, payment.id)
    if await _already_taken_back(session, payment):
        raise errors.PaymentAlreadyRefunded()
    try:
        await stripe.refund(
            payment_intent_id=payment.stripe_payment_intent_id,
            amount_pence=payment.amount_total_pence,
            idempotency_key=f"refund:{payment.id}:{payment.amount_total_pence}",
        )
    except CheckoutRefused as exc:
        raise errors.StripeRefundRefused(f"Stripe refused that refund: {exc}") from exc
    except CheckoutUnavailable as exc:
        raise errors.StripeRefundFailed() from exc
    return await refund(session, payment_id, reason=reason, actor=actor, now=now)


async def _already_taken_back(session: AsyncSession, payment: Payment) -> bool:
    """True when the access was withdrawn, Stripe already refunded the charge, or it was disputed."""
    if payment.entitlement_id is not None and await entitlement_grants.revoked_ids(
        session, [payment.entitlement_id]
    ):
        return True
    events = await repository.processed_events_for_intent(
        session,
        payment.stripe_payment_intent_id,
        ["charge.refunded", "charge.dispute.created", "charge.dispute.closed"],
    )

    def payload_object(event: StripeEvent) -> dict[str, Any]:
        return (event.payload or {}).get("data", {}).get("object") or {}

    if any(
        delivery.event_type == "charge.refunded" and domain.is_full_refund(payload_object(delivery))
        for delivery in events
    ):
        return True
    # A dispute is open until it closes; one won gave the access back and settled the matter.
    won = any(domain.restores_access(delivery.event_type, payload_object(delivery)) for delivery in events)
    return not won and any(delivery.event_type == "charge.dispute.created" for delivery in events)
