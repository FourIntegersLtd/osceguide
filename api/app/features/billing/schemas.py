from __future__ import annotations

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
    """A payment receipt, rendered.

    Every field is a string already formatted for display: a receipt is read by
    people rather than parsed by clients, and rendering money and dates in the
    browser is how two surfaces come to show the same payment differently.
    """

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
