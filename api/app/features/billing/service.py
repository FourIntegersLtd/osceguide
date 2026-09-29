"""Turning a Stripe payment into access."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.logging import get_logger
from app.features.billing import domain, errors, receipts, repository, signature
from app.features.billing.service_settlement import _as_plans, settle_payment
from app.features.growth import service as growth
from app.features.identity import service as identity

log = get_logger(__name__)


def plan_label(plan_code: str) -> str:
    """A plan code as a person reads it (`receipts.plan_label`), exposed here so
    another slice can ask for it without reaching past this service into
    `billing.receipts`, which the cross-slice import guard does not allow."""
    return receipts.plan_label(plan_code)


def verified_event(raw: bytes, header: str, *, secret: str, now: int) -> dict[str, Any]:
    """Check the signature, then parse: the signature covers the exact bytes Stripe sent, so
    parsing first and re-serialising would compare a different payload and never match."""
    try:
        signature.verify(raw, header, secret=secret, now=now)
    except signature.SigningSecretMissing as exc:
        # Fails closed. An unset secret must not mean "accept anything".
        raise errors.InvalidSignature(str(exc)) from exc
    except signature.InvalidSignature as exc:
        raise errors.InvalidSignature(str(exc)) from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise errors.InvalidWebhook("That webhook body was not JSON.") from exc
    if not isinstance(parsed, dict):
        raise errors.InvalidWebhook("A webhook body must be an object.")
    return parsed


async def handle_event(session: AsyncSession, *, event: dict[str, Any], now: datetime) -> dict[str, str]:
    """Apply one webhook delivery, at most once.

    One transaction: the ledger row, the payment and the entitlement commit together, so a
    crash between them cannot leave a customer charged without access, or granted access twice
    on Stripe's retry. A delivery that cannot be applied keeps its ledger row and the reason
    (`persist_effects`) and answers non-2xx, so Stripe's retry applies it once the cause is fixed.
    """
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")

    try:
        processed = await repository.processed_event_ids(session, event_id)
        if not domain.should_process_event(seen=processed, event_id=event_id):
            return {"status": "already_applied"}
    except domain.InvalidEvent as exc:
        raise errors.InvalidWebhook(str(exc)) from exc

    if not await repository.record_event(
        session, event_id=event_id, event_type=event_type, event_payload=event
    ):
        existing = await repository.event_by_id(session, event_id)
        if existing is not None and existing.processed_at is not None:
            # A concurrent delivery got there first and has committed.
            return {"status": "already_applied"}
        # Recorded by an earlier delivery that failed to apply: try again.

    if not domain.grants_access(event_type):
        # Acknowledged so Stripe stops delivering it, and recorded so we can see
        # what it sent us.
        await repository.mark_event_processed(session, event_id=event_id, at=now)
        return {"status": "ignored"}

    try:
        await _apply_checkout(session, event=event, now=now)
    except AppError as exc:
        await repository.mark_event_failed(session, event_id=event_id, reason=exc.message)
        raise
    await repository.mark_event_processed(session, event_id=event_id, at=now)
    return {"status": "applied"}


def _price_id(checkout_payload: dict[str, Any]) -> str:
    """Which price the customer paid for.

    A `checkout.session` object carries no top-level price: it is in `metadata.price_id` when
    checkout was created with it (ours is), or in the expanded `line_items`. A prior read of
    `checkout_payload["price_id"]` matched nothing Stripe sends, so every real delivery was
    refused.
    """
    metadata = checkout_payload.get("metadata") or {}
    if metadata.get("price_id"):
        return str(metadata["price_id"]).strip()
    for line_item in (checkout_payload.get("line_items") or {}).get("data") or []:
        price = line_item.get("price") or {}
        if price.get("id"):
            return str(price["id"]).strip()
    return ""


async def _apply_checkout(session: AsyncSession, *, event: dict[str, Any], now: datetime) -> None:
    """Turn one `checkout.session.completed` event into a settled payment and a grant.

    Raises `InvalidWebhook` for a payload missing what settlement needs, `UnknownPlanError` for
    a price with no matching plan row — both leave the ledger row in place for a retry once the
    cause is fixed (see `errors.InvalidWebhook`).
    """
    checkout_payload = (event.get("data") or {}).get("object") or {}
    email = str(
        checkout_payload.get("customer_email")
        or (checkout_payload.get("customer_details") or {}).get("email")
        or ""
    ).strip()
    price_id = _price_id(checkout_payload)
    intent_id = str(checkout_payload.get("payment_intent") or "").strip()

    if not (email and price_id and intent_id):
        raise errors.InvalidWebhook("The checkout payload lacks an email, a price or an intent.")

    user = await identity.user_ref_by_email(session, email)
    if user is None:
        # A payment for an address we do not know. The ledger row survives this
        # (see `errors.InvalidWebhook`), so it can be reconciled by hand or
        # applied on Stripe's retry once the person has registered.
        log.warning("payment for an unknown address", event_id=event.get("id"))
        raise errors.InvalidWebhook("No account for that email address.")

    plans = await repository.active_plans(session)
    try:
        plan = domain.plan_for_price(_as_plans(plans), price_id)
    except domain.UnknownPlan as exc:
        raise errors.UnknownPlanError(str(exc)) from exc

    plan_row = next(
        candidate_plan for candidate_plan in plans if candidate_plan.stripe_price_id == plan.price_id
    )
    await settle_payment(
        session,
        user=user,
        plan_row=plan_row,
        intent_id=intent_id,
        checkout_session_id=str(checkout_payload.get("id") or "") or None,
        amount_total=int(checkout_payload.get("amount_total") or plan.amount_pence),
        amount_tax=int((checkout_payload.get("total_details") or {}).get("amount_tax") or 0),
        currency=str(checkout_payload.get("currency") or "gbp"),
        receipt_url=str(checkout_payload.get("receipt_url") or "") or None,
        customer_name=(checkout_payload.get("customer_details") or {}).get("name") or user.name,
        email=email,
        now=now,
    )

    # The referral credit, in the same transaction as the payment, so it exists
    # exactly when the payment does. Only a discounted plan earns one: that is
    # the proof the checkout went through a code check (`service_checkout`).
    referral_code = str((checkout_payload.get("metadata") or {}).get("referral_code") or "").strip()
    if referral_code and domain.is_referral_plan(plan_row.code):
        await growth.credit_referral_purchase(
            session,
            code=referral_code,
            referred_user_id=user.id,
            plan_duration_days=plan_row.duration_days,
            now=now,
            plan_code=plan_row.code,
        )


async def list_plans(session: AsyncSession) -> list[dict[str, Any]]:
    """Every plan on sale, as plain dicts the router turns into `schemas.PlanRead`.

    A referral discount is not listed as a plan of its own. Its price rides on the full-price
    plan as `referral_amount_pence`, so the pricing page can show what a code would save.
    """
    plans = await repository.active_plans(session)
    referral_prices = {plan.code: plan.amount_pence for plan in plans if domain.is_referral_plan(plan.code)}
    return [
        {
            "code": plan.code,
            "amount_pence": plan.amount_pence,
            "currency": plan.currency,
            "duration_days": plan.duration_days,
            "exam_code": plan.exam_code,
            "referral_amount_pence": referral_prices.get(domain.referral_plan_code(plan.code)),
        }
        for plan in plans
        if not domain.is_referral_plan(plan.code)
    ]


async def count_payments_for_users(session: AsyncSession, user_ids: list[uuid.UUID]) -> int:
    """For the partner funnel's purchase count."""
    return await repository.count_payments_for_users(session, user_ids)


async def revenue_for_users(
    session: AsyncSession, user_ids: list[uuid.UUID], *, paid_from: datetime, paid_before: datetime
) -> int:
    """For a partner's spend report: what the people it sent paid in the window, gross."""
    return await repository.revenue_for_users(session, user_ids, paid_from=paid_from, paid_before=paid_before)
