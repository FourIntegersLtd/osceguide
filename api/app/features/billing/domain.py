"""What a payment buys.

A payment does not *mean* access; it *grants* it. The two are separate records
so a refund can revoke access without erasing the sale, and so an org grant and
a purchase can answer the same question in `entitlements`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# Oracle: `b2c payment_service.PRICE_CONFIG`. Kept as the seed for the `plans`
# table rather than as the lookup itself — what a customer bought is decided by
# the price id Stripe reports, not by reverse-engineering the amount.
DEFAULT_PLAN_DAYS = {"one_month": 30, "three_month": 90, "six_month": 180}

ACCESS_GRANTING_EVENTS = frozenset({"checkout.session.completed"})
# Money going back: the access it bought goes with it.
ACCESS_WITHDRAWING_EVENTS = frozenset({"charge.refunded", "charge.dispute.created"})

# A referral discount is its own plan row: the same exam and duration at 10% off,
# on its own Stripe price, coded as the full-price plan plus this suffix (so
# `sca_1m` is discounted by `sca_1m_referral`). A row rather than a Stripe coupon
# because settlement already turns any price id into a plan, so a discounted
# payment grants access exactly as a full-price one does.
REFERRAL_PLAN_SUFFIX = "_referral"


def referral_plan_code(plan_code: str) -> str:
    """The code of the plan that sells `plan_code` at the referral discount."""
    return f"{plan_code}{REFERRAL_PLAN_SUFFIX}"


def is_referral_plan(plan_code: str) -> bool:
    """Whether this plan is a referral discount, which is bought only with a code."""
    return plan_code.endswith(REFERRAL_PLAN_SUFFIX)


REFERRAL_DISCOUNT_PERCENT = 10


def referral_amount_pence(amount_pence: int) -> int:
    """What a plan costs with a referral code: 10% off, rounded down to the penny, as b2c priced
    it (£24.99 becomes £22.49)."""
    return amount_pence * (100 - REFERRAL_DISCOUNT_PERCENT) // 100


class UnknownPlan(LookupError):
    """A price id with no plan. Reached only after the customer has been charged, so it must
    fail loudly and leave the payment recoverable rather than granting a guessed duration."""


class InvalidEvent(ValueError):
    """A webhook delivery that cannot be reasoned about at all, such as one with no event id."""


@dataclass(frozen=True)
class Plan:
    """One thing a customer can buy: a price, a duration and the plan code that names it.

    A pure-domain shape rather than the `Plan` ORM row itself (see `service_settlement._as_plans`),
    so this module stays free of SQLAlchemy and is testable with plain values.
    """

    code: str
    price_id: str
    duration_days: int
    amount_pence: int


def plan_for_price(plans: Sequence[Plan], price_id: str) -> Plan:
    """The plan a Stripe price id names, or raise `UnknownPlan` if none of `plans` matches."""
    key = (price_id or "").strip()
    for plan in plans:
        if plan.price_id == key:
            return plan
    raise UnknownPlan(
        f"No plan for price {price_id!r}. The payment succeeded, so this needs "
        "a plan row rather than a retry."
    )


def access_window(plan: Plan, *, paid_at: datetime) -> tuple[datetime, datetime]:
    return paid_at, paid_at + timedelta(days=plan.duration_days)


def should_process_event(*, seen: Iterable[str], event_id: str) -> bool:
    """Whether this webhook delivery is new. Stripe retries until it receives a 2xx; returning
    500 on failure forces exactly that, so a retry can re-run the grant."""
    key = (event_id or "").strip()
    if not key:
        raise InvalidEvent("A webhook event must carry an id to be idempotent.")
    return key not in set(seen)


def grants_access(event_type: str) -> bool:
    """Everything else is acknowledged and ignored: a non-2xx to an event we will never act on
    just asks Stripe to keep delivering it."""
    return (event_type or "").strip() in ACCESS_GRANTING_EVENTS


def withdraws_access(event_type: str) -> bool:
    """A refund or a dispute: the payment is taken back, so the access it bought is too."""
    return (event_type or "").strip() in ACCESS_WITHDRAWING_EVENTS


def is_full_refund(charge: dict[str, Any]) -> bool:
    """Whether Stripe says the whole charge is refunded. A partial refund leaves the access."""
    amount = int(charge.get("amount") or 0)
    return bool(charge.get("refunded")) or (amount > 0 and int(charge.get("amount_refunded") or 0) >= amount)


# --- invoices (E-22) ----------------------------------------------------------

INVOICE_ISSUED = "issued"
INVOICE_PAID = "paid"
INVOICE_VOID = "void"

# Which way an invoice may move. Paid and void are final: a mistake on a paid
# invoice is a credit note, not an edit, and a void number is never reused.
_INVOICE_MOVES = {INVOICE_ISSUED: frozenset({INVOICE_PAID, INVOICE_VOID})}


class InvoiceNotEditable(ValueError):
    """Raised when an invoice is asked to move from a final state."""


class InvalidInvoiceLine(ValueError):
    """Raised when a line has no amount and no payment to take one from."""


def invoice_number(*, year: int, sequence: int) -> str:
    """`INV-2026-000123`: the year it was raised, and a number never used before."""
    return f"INV-{year}-{sequence:06d}"


def ensure_invoice_move(current: str, target: str) -> None:
    """Refuse a status change the invoice cannot make; staying put is allowed."""
    if current == target:
        return
    if target not in _INVOICE_MOVES.get(current, frozenset()):
        raise InvoiceNotEditable(f"An invoice that is {current} cannot become {target}.")


def ensure_po_editable(status: str) -> None:
    """A PO number may be added or corrected until the invoice is paid or void."""
    if status != INVOICE_ISSUED:
        raise InvoiceNotEditable(f"An invoice that is {status} is final.")


def line_amount(*, quantity: int, unit_amount_pence: int) -> int:
    """What one line comes to."""
    return quantity * unit_amount_pence
