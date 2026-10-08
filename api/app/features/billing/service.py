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
from app.features.billing.service_settlement import (
    _as_plans,
    restore_payment,
    settle_payment,
    withdraw_payment,
)
from app.features.catalog import service_import as catalog_import
from app.features.entitlements import service as entitlements
from app.features.growth import service as growth
from app.features.identity import service as identity

log = get_logger(__name__)


_NO_ACCOUNT_FOR_PAYER = "No account for that email address."


async def _apply_withdrawal(session: AsyncSession, *, event: dict[str, Any], now: datetime) -> bool:
    """A refund or a dispute: withdraw what the payment bought (`withdraw_payment`).

    False when nothing changes: a partial refund, or a payment already withdrawn. Raises
    `PaymentNotYetRecorded` when no payment is recorded for the charge yet, which can be the
    checkout event arriving after this one; the delivery is refused so Stripe retries it.
    A dispute won is `_apply_restoration`.
    """
    charge = (event.get("data") or {}).get("object") or {}
    if event.get("type") == "charge.refunded" and not domain.is_full_refund(charge):
        return False
    payment = await repository.payment_by_intent(session, str(charge.get("payment_intent") or ""))
    if payment is None:
        raise errors.PaymentNotYetRecorded()

    async def revoke(entitlement_id: uuid.UUID) -> None:
        await entitlements.withdraw(session, entitlement_id, now=now)

    return await withdraw_payment(session, payment, revoke=revoke, now=now)


async def _apply_restoration(session: AsyncSession, *, event: dict[str, Any]) -> bool:
    """A dispute won: give the payment's access and referral credit back (`restore_payment`).
    Refused for a retry when the payment is not recorded yet, like a withdrawal."""
    charge = (event.get("data") or {}).get("object") or {}
    payment = await repository.payment_by_intent(session, str(charge.get("payment_intent") or ""))
    if payment is None:
        raise errors.PaymentNotYetRecorded()
    return await restore_payment(session, payment)


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

    if domain.restores_access(event_type, (event.get("data") or {}).get("object") or {}):
        try:
            restored = await _apply_restoration(session, event=event)
        except AppError as exc:
            await repository.mark_event_failed(session, event_id=event_id, reason=exc.message)
            raise
        await repository.mark_event_processed(session, event_id=event_id, at=now)
        return {"status": "applied" if restored else "ignored"}

    if domain.withdraws_access(event_type):
        try:
            withdrawn = await _apply_withdrawal(session, event=event, now=now)
        except AppError as exc:
            await repository.mark_event_failed(session, event_id=event_id, reason=exc.message)
            raise
        await repository.mark_event_processed(session, event_id=event_id, at=now)
        return {"status": "applied" if withdrawn else "ignored"}

    if not domain.grants_access(event_type):
        # Acknowledged so Stripe stops delivering it, and recorded so we can see
        # what it sent us.
        await repository.mark_event_processed(session, event_id=event_id, at=now)
        return {"status": "ignored"}

    try:
        applied = await _apply_checkout(session, event=event, now=now)
    except AppError as exc:
        await repository.mark_event_failed(session, event_id=event_id, reason=exc.message)
        raise
    if not applied:
        # S-4: the customer has paid; refusing the delivery would only have
        # Stripe retry it for three days and then give up. It is acknowledged
        # and left in the reconcile queue (`failed_only`), where support finds
        # it by address and replays it, or records it against the right account.
        await repository.mark_event_failed(session, event_id=event_id, reason=_NO_ACCOUNT_FOR_PAYER)
        return {"status": "needs_attention"}
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


async def _user_from_checkout(
    session: AsyncSession, payload: dict[str, Any], email: str | None
) -> identity.UserRef | None:
    """The person who started the checkout, by id: the address Stripe echoes is the one they had
    then, and they may have changed it since. The address only finds older sessions."""
    reference = str(payload.get("client_reference_id") or "").strip()
    if reference:
        try:
            found = await identity.user_ref_by_id(session, uuid.UUID(reference))
        except ValueError:
            found = None
        if found is not None:
            return found
    return await identity.user_ref_by_email(session, email) if email else None


async def _apply_checkout(session: AsyncSession, *, event: dict[str, Any], now: datetime) -> bool:
    """Turn one `checkout.session.completed` event into a settled payment and a grant.

    False, and nothing settled, when the payer's address matches no account: that is a paid
    session needing a person, not a bad delivery. Raises `InvalidWebhook` for a payload missing
    a price or an intent, `UnknownPlanError` for a price with no matching plan row — both leave
    the ledger row in place for a retry once the cause is fixed (see `errors.InvalidWebhook`).
    """
    checkout_payload = (event.get("data") or {}).get("object") or {}
    email = str(
        checkout_payload.get("customer_email")
        or (checkout_payload.get("customer_details") or {}).get("email")
        or ""
    ).strip()
    price_id = _price_id(checkout_payload)
    intent_id = str(checkout_payload.get("payment_intent") or "").strip()

    if not (price_id and intent_id):
        raise errors.InvalidWebhook("The checkout payload lacks a price or an intent.")

    user = await _user_from_checkout(session, checkout_payload, email)
    if user is None:
        log.warning("payment for an unknown address", event_id=event.get("id"))
        return False

    # Every plan, retired ones too: taking a plan off sale must not refuse a payment for it
    # that was already under way.
    plans = await repository.all_plans(session)
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
    return True


async def list_plans(session: AsyncSession) -> list[dict[str, Any]]:
    """Every plan on sale, as plain dicts the router turns into `schemas.PlanRead`.

    A referral discount is not listed as a plan of its own. Its price rides on the full-price
    plan as `referral_amount_pence`, so the pricing page can show what a code would save.
    """
    plans = await repository.active_plans(session)
    stations = await catalog_import.published_station_counts_by_code(
        session, sorted({plan.exam_code for plan in plans})
    )
    referral_prices = {plan.code: plan.amount_pence for plan in plans if domain.is_referral_plan(plan.code)}
    return [
        {
            "code": plan.code,
            "amount_pence": plan.amount_pence,
            "currency": plan.currency,
            "duration_days": plan.duration_days,
            "exam_code": plan.exam_code,
            "referral_amount_pence": referral_prices.get(domain.referral_plan_code(plan.code)),
            "station_count": stations[plan.exam_code],
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


async def payer_user_ids_among(
    session: AsyncSession, user_ids: list[uuid.UUID], *, paid_from: datetime, paid_before: datetime
) -> set[uuid.UUID]:
    """For a partner breakdown: which of these acquired users paid at least once in the window."""
    return await repository.payer_user_ids_among(
        session, user_ids, paid_from=paid_from, paid_before=paid_before
    )


async def revenue_breakdown_for_users(
    session: AsyncSession, user_ids: list[uuid.UUID], *, paid_from: datetime, paid_before: datetime
) -> list[tuple[str | None, int, int]]:
    """For a partner's revenue report: what these people paid in the window, split by
    plan code. A `None` plan code is a payment whose plan has since been deleted."""
    return await repository.revenue_breakdown_for_users(
        session, user_ids, paid_from=paid_from, paid_before=paid_before
    )


async def revenue_over_time_for_users(
    session: AsyncSession,
    user_ids: list[uuid.UUID],
    *,
    paid_from: datetime,
    paid_before: datetime,
    bucket: str,
) -> list[tuple[datetime, int, int]]:
    """For a partner's revenue-over-time chart: gross revenue and payment count per bucket.

    `bucket` is `day`, `week` or `month` — passed straight to Postgres'
    `date_trunc`, so the caller must have already validated it.
    """
    return await repository.revenue_over_time_for_users(
        session, user_ids, paid_from=paid_from, paid_before=paid_before, bucket=bucket
    )
