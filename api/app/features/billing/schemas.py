"""The shapes billing sends and receives: plans, checkout, receipts, and payments for platform staff."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlanRead(BaseModel):
    code: str
    amount_pence: int
    currency: str
    duration_days: int
    exam_code: str | None


class WebhookResult(BaseModel):
    status: str


class ReceiptRead(BaseModel):
    """A payment receipt, rendered. Every field is a string already formatted for display, so
    two clients cannot render the same payment differently."""

    receipt_id: str
    customer_email: str
    customer_name: str
    exam_code: str
    plan_label: str
    plan_start_date: str
    plan_end_date: str
    paid_at: str
    amount_subtotal: str
    amount_tax: str
    amount_total: str
    show_tax_row: bool
    currency: str
    stripe_reference: str
    stripe_receipt_url: str | None = None
    seller_name: str
    footer_extra: str


class StartCheckout(BaseModel):
    """Which plan to buy. A code, never a price: the plan row owns the price."""

    plan_code: str = Field(min_length=1, max_length=32)


class CheckoutStarted(BaseModel):
    """Where to send the customer. Nothing is granted until the webhook."""

    checkout_url: str


class PlatformPaymentRead(BaseModel):
    """A payment as the console reads it: raw amounts, both references, what it bought."""

    id: uuid.UUID
    user_id: uuid.UUID
    receipt_id: str | None
    stripe_payment_intent_id: str
    checkout_session_id: str | None
    amount_total_pence: int
    amount_tax_pence: int
    currency: str
    paid_at: datetime
    plan_code: str | None
    plan_starts_at: datetime | None
    plan_ends_at: datetime | None
    entitlement_id: uuid.UUID | None
    receipt_url: str | None
    customer_email: str | None


class StripeEventRead(BaseModel):
    """One webhook delivery from the ledger, with the fields support reads
    out of the payload rather than the whole document."""

    event_id: str
    event_type: str
    received_at: datetime
    processed_at: datetime | None
    failure: str | None
    customer_email: str | None
    price_id: str | None
    payment_intent_id: str | None


class RecordManualPayment(BaseModel):
    """A payment that did not come through Stripe — a bank transfer, a sponsor,
    a comped seat — recorded so it grants access, mints a receipt and counts
    like any other. Without a reference one is minted as `manual:<id>`."""

    plan_code: str = Field(min_length=1, max_length=32)
    stripe_payment_intent_id: str | None = Field(default=None, min_length=1, max_length=100)
    amount_total_pence: int | None = Field(default=None, ge=0)
    paid_at: datetime | None = None
    note: str = Field(min_length=1, max_length=500)


class RefundRequest(BaseModel):
    """Record-only: the money is returned in the Stripe dashboard. This revokes
    what the payment bought and says so in the audit log; the payment row stays."""

    reason: str = Field(min_length=1, max_length=500)
