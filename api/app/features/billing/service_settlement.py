"""Turning one paid-for plan into access, a payment row and a receipt.

Shared by two callers that must take exactly the same steps: the webhook, for a card payment
Stripe reports, and the platform console, for a payment that did not come through Stripe at all
(a bank transfer, a sponsor, a comped seat). One function is how the console stays in step.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import domain, errors, receipts, repository
from app.features.billing.models import Payment, Plan
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.notifications import service as notifications


def _as_plans(plan_rows: list[Plan]) -> list[domain.Plan]:
    """The stored `Plan` ORM rows, translated into the domain's plain `domain.Plan` shape."""
    return [
        domain.Plan(
            code=plan_row.code,
            price_id=plan_row.stripe_price_id,
            duration_days=plan_row.duration_days,
            amount_pence=plan_row.amount_pence,
        )
        for plan_row in plan_rows
    ]


async def settle_payment(
    session: AsyncSession,
    *,
    user: identity.UserRef,
    plan_row: Plan,
    intent_id: str,
    checkout_session_id: str | None,
    amount_total: int,
    amount_tax: int,
    currency: str,
    receipt_url: str | None,
    customer_name: str,
    email: str,
    now: datetime,
) -> Payment:
    """Turn one paid-for plan into access, a payment row and a receipt.

    Also used by the platform console for a payment that did not come through Stripe, so it
    takes exactly the same steps as the webhook.
    """
    if not plan_row.exam_code:
        # Defaulting to one exam here silently sold the wrong thing (B-2). The
        # column is NOT NULL now; a row from before that holds '' and lands here.
        raise errors.UnknownPlanError(f"Plan {plan_row.code!r} names no exam, so there is nothing to grant.")
    plan = _as_plans([plan_row])[0]
    starts_at, ends_at = domain.access_window(plan, paid_at=now)

    granted = await entitlements.grant(
        session,
        user_id=user.id,
        exam_code=plan_row.exam_code,
        source="purchase",
        source_ref=intent_id,
        ends_at=ends_at,
    )
    # Our own receipt, minted here so it exists from the moment the payment
    # does. A receipt created on demand later would have no stable id, and the
    # id is what a customer quotes to support.
    receipt_id = receipts.new_receipt_id(plan_row.exam_code)
    payment = await repository.record_payment(
        session,
        user_id=user.id,
        plan_id=plan_row.id,
        stripe_payment_intent_id=intent_id,
        checkout_session_id=checkout_session_id,
        amount_total_pence=amount_total,
        currency=currency,
        receipt_url=receipt_url,
        paid_at=now,
        entitlement_id=granted.id,
        receipt_id=receipt_id,
        customer_email=email,
        customer_name=customer_name,
        amount_tax_pence=amount_tax,
        plan_starts_at=starts_at,
        plan_ends_at=ends_at,
    )

    # The receipt reaches the customer. Its fields were minted above and read
    # back through `/me/receipts` from the day billing landed, and nothing
    # ever sent one — a person paid and heard nothing from us at all.
    #
    # Queued on the outbox in this transaction, like every other message, so
    # a webhook that rolls back cannot leave a receipt for a payment that did
    # not happen, and a mail provider being briefly down does not lose it.
    await notifications.enqueue_email(
        session,
        recipient=email,
        subject="Your OSCE Guide receipt",
        template_key="payment_receipt",
        payload=receipts.receipt_fields(
            receipts.PaymentRecord(
                receipt_id=receipt_id,
                customer_email=email,
                customer_name=customer_name,
                exam_code=plan_row.exam_code,
                plan_code=plan_row.code,
                amount_total_pence=amount_total,
                amount_tax_pence=amount_tax,
                currency=currency,
                paid_at=now,
                plan_starts_at=starts_at,
                plan_ends_at=ends_at,
                stripe_payment_intent_id=intent_id,
                stripe_receipt_url=receipt_url,
            )
        ),
        # One receipt per payment, however many times Stripe delivers it.
        idempotency_key=f"payment_receipt:{intent_id}",
    )
    return payment
