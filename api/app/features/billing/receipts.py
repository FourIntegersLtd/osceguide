"""What a customer is shown for a payment they made.

Financial output, so every format here is an oracle rather than a preference:
`tests/unit/test_receipt_oracle.py` pins each one against the legacy helper it came from.

- A receipt is built from the payment record and nothing else — no live user lookup — so a
  customer who later changes their name still gets the receipt as it was issued. That is why
  `customer_name` is stored on the payment rather than looked up.
- It is a receipt, not a VAT invoice, and it says so; the footer is not decoration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

# Oracle: `plan_duration_label`. The label a customer recognises, not the code.
PLAN_LABELS = {
    "one_month": "1-Month Access",
    "three_month": "3-Month Access",
    "six_month": "6-Month Access",
    "test": "Test Plan",
}

SELLER_NAME = "Four Integers Ltd"

# Oracle: the legacy footer, verbatim. It is the line that keeps this document
# from being mistaken for a tax invoice.
FOOTER = (
    "Payment reference on file for support verification. This is a payment receipt, not a VAT tax invoice."
)

# Oracle: `stripe_reference_display`. Long references are shown by their tail,
# which is what a customer reads out to support.
_REFERENCE_FULL_LENGTH = 20
_REFERENCE_TAIL = 12


def new_receipt_id(exam_code: str, *, token: str | None = None) -> str:
    """Oracle: `generate_receipt_id` — `RCP-<exam>-<8 hex>`.

    The exam is in the id on purpose: support reads these aloud, and knowing which product a
    receipt belongs to without opening it saves a round trip.
    """
    suffix = token if token is not None else uuid.uuid4().hex[:8]
    return f"RCP-{exam_code.strip().lower()}-{suffix}"


def format_amount_gbp(amount_pence: int | None) -> str:
    """Oracle: `format_amount_gbp`. A dash for nothing, never `£0.00`."""
    if amount_pence is None:
        return "-"
    return f"£{amount_pence / 100:.2f}"


def format_receipt_date(value: datetime | None) -> str:
    """Oracle: `format_receipt_date` — `01 January 2025`. Spelled out rather than numeric,
    because `01/02/2025` is two different days on either side of the Atlantic."""
    if value is None:
        return "-"
    return value.strftime("%d %B %Y")


def plan_label(plan_code: str) -> str:
    """Oracle: `plan_duration_label`, including its fallback."""
    return PLAN_LABELS.get(plan_code, plan_code.replace("_", " "))


def stripe_reference_display(payment_intent_id: str | None) -> str:
    """Oracle: `stripe_reference_display`."""
    if not payment_intent_id:
        return "-"
    if len(payment_intent_id) <= _REFERENCE_FULL_LENGTH:
        return payment_intent_id
    return f"…{payment_intent_id[-_REFERENCE_TAIL:]}"


@dataclass(frozen=True)
class PaymentRecord:
    """The stored payment a receipt is rendered from, and only that."""

    receipt_id: str
    customer_email: str
    customer_name: str
    exam_code: str
    plan_code: str
    amount_total_pence: int
    amount_tax_pence: int
    currency: str
    paid_at: datetime
    plan_starts_at: datetime | None
    plan_ends_at: datetime | None
    stripe_payment_intent_id: str | None
    stripe_receipt_url: str | None


def receipt_fields(record: PaymentRecord) -> dict[str, object]:
    """Oracle: `build_receipt_template_data_from_record`.

    The subtotal is derived rather than stored — total minus tax, floored at zero — so it can
    never disagree with the amount actually taken.
    """
    subtotal = max(record.amount_total_pence - record.amount_tax_pence, 0)
    return {
        "receipt_id": record.receipt_id,
        "customer_email": record.customer_email,
        "customer_name": record.customer_name,
        "exam_code": record.exam_code,
        "plan_label": plan_label(record.plan_code),
        "plan_start_date": format_receipt_date(record.plan_starts_at),
        "plan_end_date": format_receipt_date(record.plan_ends_at),
        "paid_at": format_receipt_date(record.paid_at),
        "amount_subtotal": format_amount_gbp(subtotal),
        "amount_tax": format_amount_gbp(record.amount_tax_pence),
        "amount_total": format_amount_gbp(record.amount_total_pence),
        # No tax, no row. A `£0.00` tax line invites the question this document
        # exists to avoid.
        "show_tax_row": record.amount_tax_pence > 0,
        "currency": (record.currency or "gbp").upper(),
        "stripe_reference": stripe_reference_display(record.stripe_payment_intent_id),
        "stripe_receipt_url": record.stripe_receipt_url,
        "seller_name": SELLER_NAME,
        "footer_extra": FOOTER,
    }
