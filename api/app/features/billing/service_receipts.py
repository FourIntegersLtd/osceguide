"""Reading back the receipt for a payment.

Kept apart from `service.py` along the actor: that module is Stripe telling us a payment
happened, this one is a customer asking for the document.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import errors, receipts, repository
from app.features.billing.models import Payment
from app.features.billing.receipt_document import render_receipt_html
from app.features.billing.schemas import ReceiptRead


async def read_receipt(session: AsyncSession, user_id: uuid.UUID, receipt_id: str) -> ReceiptRead:
    """One of this person's receipts. Scoped to the caller: a receipt id is short and printed on
    a document that gets forwarded, so it must not be a key anybody holding it can read."""
    payment = await repository.payment_by_receipt_id(session, user_id, receipt_id)
    if payment is None or payment.receipt_id is None:
        raise errors.ReceiptNotFound()

    return await _receipt_of(session, payment, payment.receipt_id)


async def _receipt_of(session: AsyncSession, payment: Payment, receipt_id: str) -> ReceiptRead:
    """The rendered receipt for a payment, under the receipt id it was minted with."""
    plan = await repository.plan_by_id(session, payment.plan_id) if payment.plan_id else None

    record = receipts.PaymentRecord(
        receipt_id=receipt_id,
        customer_email=payment.customer_email or "",
        customer_name=payment.customer_name or "",
        exam_code=plan.exam_code or "" if plan else "",
        plan_code=plan.code if plan else "",
        amount_total_pence=payment.amount_total_pence,
        amount_tax_pence=payment.amount_tax_pence,
        currency=payment.currency,
        paid_at=payment.paid_at,
        plan_starts_at=payment.plan_starts_at,
        plan_ends_at=payment.plan_ends_at,
        stripe_payment_intent_id=payment.stripe_payment_intent_id,
        stripe_receipt_url=payment.receipt_url,
    )
    return ReceiptRead(**receipts.receipt_fields(record))


async def read_receipt_document(session: AsyncSession, user_id: uuid.UUID, receipt_id: str) -> str:
    """The same receipt, as a document somebody can print or keep. Rendered from the same
    fields the JSON carries, so the two can never disagree about what was charged."""
    receipt = await read_receipt(session, user_id, receipt_id)
    return render_receipt_html(receipt.model_dump())


async def list_my_receipts(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    cursor: dict[str, Any] | None,
    checkout_session_id: str | None = None,
) -> tuple[list[str], str | None]:
    """A page of this person's receipt ids, newest first, and the cursor for the next page."""
    payments, next_cursor = await repository.payments_page(
        session, user_id, limit=limit, cursor=cursor, checkout_session_id=checkout_session_id
    )
    return [str(payment.receipt_id) for payment in payments], next_cursor


async def list_my_receipts_whole(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[ReceiptRead], str | None]:
    """A page of this person's rendered receipts in one go, so the account page needs no call per id."""
    payments, next_cursor = await repository.payments_page(session, user_id, limit=limit, cursor=cursor)
    return [await _receipt_of(session, payment, str(payment.receipt_id)) for payment in payments], next_cursor


async def export_payments_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Every payment this person has made, shaped for the `/me/export` download.

    Kept to what a person needs to see, not the Stripe identifiers a support
    agent would use to look a charge up.
    """
    return [
        {
            "receipt_id": payment.receipt_id,
            "amount_total_pence": payment.amount_total_pence,
            "amount_tax_pence": payment.amount_tax_pence,
            "currency": payment.currency,
            "receipt_url": payment.receipt_url,
            "paid_at": payment.paid_at,
        }
        for payment in await repository.payments_for_user(session, user_id)
    ]
