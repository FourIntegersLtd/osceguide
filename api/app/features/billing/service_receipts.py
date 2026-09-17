"""Reading back the receipt for a payment.

Split from `service.py` along the actor: that module is Stripe telling us a
payment happened, this one is a customer asking for the document. They change
for entirely different reasons — a webhook shape, and what a receipt has to
show.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.billing import errors, receipts, repository
from app.features.billing.schemas import ReceiptRead


async def read_receipt(session: AsyncSession, user_id: uuid.UUID, receipt_id: str) -> ReceiptRead:
    """One of this person's receipts.

    Scoped to the caller: a receipt id is short and printed on a document that
    gets forwarded to accountants and employers, so it must not be a key
    anybody holding it can read.
    """
    row = await repository.payment_by_receipt_id(session, user_id, receipt_id)
    if row is None or row.receipt_id is None:
        raise errors.ReceiptNotFound()

    plan = await repository.plan_by_id(session, row.plan_id) if row.plan_id else None

    record = receipts.PaymentRecord(
        receipt_id=row.receipt_id,
        customer_email=row.customer_email or "",
        customer_name=row.customer_name or "",
        exam_code=plan.exam_code or "" if plan else "",
        plan_code=plan.code if plan else "",
        amount_total_pence=row.amount_total_pence,
        amount_tax_pence=row.amount_tax_pence,
        currency=row.currency,
        paid_at=row.paid_at,
        plan_starts_at=row.plan_starts_at,
        plan_ends_at=row.plan_ends_at,
        stripe_payment_intent_id=row.stripe_payment_intent_id,
        stripe_receipt_url=row.receipt_url,
    )
    return ReceiptRead(**receipts.receipt_fields(record))


async def list_my_receipts(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """The receipt ids this person has, newest first."""
    return [
        row.receipt_id
        for row in await repository.payments_for_user(session, user_id)
        if row.receipt_id is not None
    ]
