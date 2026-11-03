"""The shapes billing sends and receives: plans, checkout, receipts, and payments for platform staff."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PlanRead(BaseModel):
    code: str
    amount_pence: int
    currency: str
    duration_days: int
    exam_code: str
    # What this plan costs with a referral code, or None when it has no
    # referral discount. The discounted plan is not listed on its own.
    referral_amount_pence: int | None = None
    # Published library stations for this plan's exam, so a price card can say what it buys.
    station_count: int = 0


class PlatformPlanRead(BaseModel):
    """A full-price plan as staff manage it, on sale or retired, with its referral twin's price."""

    code: str
    exam_code: str
    amount_pence: int
    currency: str
    duration_days: int
    active: bool
    stripe_price_id: str
    referral_amount_pence: int | None = None
    # How many library stations this plan unlocks, already counting the 3 free-trial
    # stations. None means every station is unlocked.
    station_limit: int | None = None
    created_at: datetime


class CreatePlan(BaseModel):
    """A new price for an exam. The Stripe prices, and the 10%-off referral twin, are made for it.

    The code is at most 23 characters so the twin's code, the code plus `_referral`, still fits.
    """

    exam_code: str = Field(min_length=1, max_length=32)
    code: str = Field(pattern=r"^[a-z0-9][a-z0-9_]*$", min_length=2, max_length=23)
    # Stripe's own floor for GBP is 30p; nothing real is priced under a pound.
    amount_pence: int = Field(ge=100, le=1_000_000)
    duration_days: int = Field(ge=1, le=730)
    # How many library stations this plan unlocks, counting the 3 free-trial stations.
    # Left out (or None) means no limit: every station is unlocked.
    station_limit: int | None = Field(default=None, ge=1, le=10000)


class UpdatePlan(BaseModel):
    """A staff change to a plan: take it on or off sale, and/or set how many stations it unlocks.

    Leaving `station_limit` out of the request body means "do not change it"; sending it
    explicitly as `null` means "no limit". The handler tells the two apart with
    `"station_limit" in body.model_fields_set`, not by checking for `None`.
    """

    active: bool | None = None
    station_limit: int | None = Field(default=None, ge=1, le=10000)


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
    # Somebody else's referral code, for 10% off. Checked before Stripe is called.
    referral_code: str | None = Field(default=None, max_length=32)


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
    # The grant this payment bought has been withdrawn (a refund or a dispute); the sale stays.
    access_revoked: bool
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
    # Omitted or 0 is free access: still a plan-linked purchase, so the plan's limit applies.
    amount_total_pence: int | None = Field(default=None, ge=0)
    paid_at: datetime | None = None
    note: str = Field(min_length=1, max_length=500)
    # The receipt email is queued only when true; a manual payment is silent by default.
    send_receipt: bool = False
    # "after_current" queues the plan behind the running one; "now" starts it at once, alongside.
    start: Literal["now", "after_current"] = "after_current"


class RefundRequest(BaseModel):
    """Record-only: the money is returned in the Stripe dashboard. This revokes
    what the payment bought and says so in the audit log; the payment row stays."""

    reason: str = Field(min_length=1, max_length=500)


# One line to put on a new invoice. Either an amount, or a settled payment to bill for.
class CreateInvoiceLine(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=300)
    quantity: int = Field(default=1, ge=1, le=100_000)
    # Pence per unit. Taken from the payment when a payment is named and this is not.
    unit_amount_pence: int | None = Field(default=None, ge=0)
    payment_id: uuid.UUID | None = None


class CreateInvoice(BaseModel):
    """An invoice for an organisation. The number is assigned; the PO number may come later."""

    po_number: str | None = Field(default=None, min_length=1, max_length=64)
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    currency: str = Field(default="gbp", pattern="^[a-z]{3}$")
    lines: list[CreateInvoiceLine] = Field(min_length=1, max_length=200)


class UpdateInvoice(BaseModel):
    """What the console may change: the PO number while issued, and the status."""

    po_number: str | None = Field(default=None, min_length=1, max_length=64)
    # `paid` or `void`, from `issued` only.
    status: str | None = Field(default=None, pattern="^(issued|paid|void)$")


# The organisation's finance team quoting their purchase order.
class SetPoNumber(BaseModel):
    po_number: str = Field(min_length=1, max_length=64)


class InvoiceLineRead(BaseModel):
    position: int
    description: str
    quantity: int
    unit_amount_pence: int
    amount_pence: int
    payment_id: uuid.UUID | None = None


class InvoiceRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    invoice_number: str
    po_number: str | None
    customer_name: str
    status: str
    currency: str
    total_pence: int
    issued_at: datetime
    due_at: datetime | None
    paid_at: datetime | None
    voided_at: datetime | None
    notes: str | None
    lines: list[InvoiceLineRead]


class PlatformAccessGrantRead(BaseModel):
    """One grant behind an exam's access, with the plan it was bought as (None when not a purchase)."""

    entitlement_id: uuid.UUID
    source: str
    plan_code: str | None
    # The plan-linked payment that bought it, so Refund needs no payment lookup (None otherwise).
    payment_id: uuid.UUID | None
    # That payment's reference (`pi_...` from Stripe, otherwise `manual:...`), which decides how a
    # refund is made.
    payment_reference: str | None
    starts_at: datetime
    ends_at: datetime | None
    revoked_at: datetime | None
    live: bool


class PlatformExamAccessRead(BaseModel):
    """What one exam lets this person do, and why: the library cap, the stations sat against it and
    the grant that decides it."""

    exam_code: str
    # None means every station is open.
    station_limit: int | None
    stations_sat: int
    # `plan:<code>`, `unlimited:<source of the other live grant>` or `no_access`.
    limit_reason: str
    grants: list[PlatformAccessGrantRead]
