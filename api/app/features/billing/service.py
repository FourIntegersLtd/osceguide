"""Turning a Stripe payment into access."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.features.billing import domain, errors, repository
from app.features.billing.models import Plan
from app.features.entitlements import service as entitlements
from app.features.identity import repository as identity_repo

log = get_logger(__name__)


def _as_plans(rows: list[Plan]) -> list[domain.Plan]:
    return [
        domain.Plan(
            code=r.code,
            price_id=r.stripe_price_id,
            duration_days=r.duration_days,
            amount_pence=r.amount_pence,
        )
        for r in rows
    ]


async def handle_event(session: AsyncSession, *, event: dict[str, Any], now: datetime) -> dict[str, str]:
    """Apply one webhook delivery, at most once.

    The whole operation is one transaction: the ledger row, the payment and the
    entitlement commit together, so a crash between them cannot leave a customer
    charged without access, or granted access twice on Stripe's retry.
    """
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")

    try:
        seen = await repository.seen_event_ids(session, event_id)
        if not domain.should_process_event(seen=seen, event_id=event_id):
            return {"status": "already_applied"}
    except domain.InvalidEvent as exc:
        raise errors.InvalidWebhook(str(exc)) from exc

    await repository.record_event(session, event_id=event_id, event_type=event_type, payload=event)

    if not domain.grants_access(event_type):
        # Acknowledged so Stripe stops delivering it, and recorded so we can see
        # what it sent us.
        await repository.mark_event_processed(session, event_id=event_id, at=now)
        return {"status": "ignored"}

    await _apply_checkout(session, event=event, now=now)
    await repository.mark_event_processed(session, event_id=event_id, at=now)
    return {"status": "applied"}


async def _apply_checkout(session: AsyncSession, *, event: dict[str, Any], now: datetime) -> None:
    payload = (event.get("data") or {}).get("object") or {}
    email = str(
        payload.get("customer_email") or (payload.get("customer_details") or {}).get("email") or ""
    ).strip()
    price_id = str(payload.get("price_id") or "").strip()
    intent_id = str(payload.get("payment_intent") or "").strip()

    if not (email and price_id and intent_id):
        raise errors.InvalidWebhook("The checkout payload lacks an email, a price or an intent.")

    user = await identity_repo.user_by_email(session, email)
    if user is None:
        # A payment for an address we do not know. Recorded as an unprocessed
        # event rather than dropped, so it can be reconciled by hand.
        log.warning("payment for an unknown address", event_id=event.get("id"))
        raise errors.InvalidWebhook("No account for that email address.")

    plans = await repository.active_plans(session)
    try:
        plan = domain.plan_for_price(_as_plans(plans), price_id)
    except domain.UnknownPlan as exc:
        raise errors.UnknownPlanError(str(exc)) from exc

    plan_row = next(r for r in plans if r.stripe_price_id == plan.price_id)
    starts_at, ends_at = domain.access_window(plan, paid_at=now)

    granted = await entitlements.grant(
        session,
        user_id=user.id,
        exam_code=plan_row.exam_code or "sca",
        source="purchase",
        source_ref=intent_id,
        ends_at=ends_at,
    )
    await repository.record_payment(
        session,
        user_id=user.id,
        plan_id=plan_row.id,
        stripe_payment_intent_id=intent_id,
        checkout_session_id=str(payload.get("id") or "") or None,
        amount_total_pence=int(payload.get("amount_total") or plan.amount_pence),
        currency=str(payload.get("currency") or "gbp"),
        receipt_url=str(payload.get("receipt_url") or "") or None,
        paid_at=now,
        entitlement_id=granted.id,
    )


async def list_plans(session: AsyncSession) -> list[dict[str, Any]]:
    return [
        {
            "code": r.code,
            "amount_pence": r.amount_pence,
            "currency": r.currency,
            "duration_days": r.duration_days,
            "exam_code": r.exam_code,
        }
        for r in await repository.active_plans(session)
    ]
