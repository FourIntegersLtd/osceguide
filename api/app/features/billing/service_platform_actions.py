"""What support may do about a payment, once `service_platform` has said what happened.

Three actions: replay a delivery that was refused once the cause is fixed, record a payment
that never went through Stripe, and mark a refund (See ADR 0012). Nothing here calls Stripe;
the money itself moves in the Stripe dashboard.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError
from app.features.billing import errors, repository, service, service_platform, service_settlement
from app.features.billing.schemas import PlatformPaymentRead
from app.features.entitlements import service_platform as entitlements
from app.features.identity import service as identity
from app.features.tenancy import service_audit


async def replay_event(
    session: AsyncSession, event_id: str, *, actor: Principal, now: datetime
) -> dict[str, str]:
    """Apply a recorded delivery again. `handle_event` is already idempotent — an applied event
    answers `already_applied` — so this cannot grant twice."""
    row = await repository.event_by_id(session, event_id)
    if row is None:
        raise errors.BillingEventNotFound()
    try:
        result = await service.handle_event(session, event=dict(row.payload or {}), now=now)
    except AppError as exc:
        await _audit_replay(session, actor, event_id, outcome=exc.code)
        raise
    await _audit_replay(session, actor, event_id, outcome=result["status"])
    return result


async def _audit_replay(session: AsyncSession, actor: Principal, event_id: str, *, outcome: str) -> None:
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
    return service_platform._payment_read(payment, plan_code=plan_row.code)


async def refund(
    session: AsyncSession, payment_id: uuid.UUID, *, reason: str, actor: Principal, now: datetime
) -> PlatformPaymentRead:
    """Record that a payment was refunded: the access it bought is withdrawn. The payment row
    stays, its `entitlement_id` still pointing at the revoked grant. Twice is once."""
    payment = await repository.payment_by_id(session, payment_id)
    if payment is None:
        raise errors.PaymentNotFound()
    if payment.entitlement_id is not None:
        await entitlements.revoke(
            session, payment.entitlement_id, reason=f"refund: {reason}", actor=actor, now=now
        )
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
    return service_platform._payment_read(payment, plan_code=plan.code if plan else None)
