"""What a payment buys.

A payment does not *mean* access; it *grants* it. The two are separate records
so a refund can revoke access without erasing the sale, and so an org grant and
a purchase can answer the same question in `entitlements`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

# Oracle: `b2c payment_service.PRICE_CONFIG`. Kept as the seed for the `plans`
# table rather than as the lookup itself — what a customer bought is decided by
# the price id Stripe reports, not by reverse-engineering the amount.
DEFAULT_PLAN_DAYS = {"one_month": 30, "three_month": 90, "six_month": 180}

ACCESS_GRANTING_EVENTS = frozenset({"checkout.session.completed"})


class UnknownPlan(LookupError):
    """A price id with no plan. Reached only after the customer has been charged, so it must
    fail loudly and leave the payment recoverable rather than granting a guessed duration."""


class InvalidEvent(ValueError):
    pass


@dataclass(frozen=True)
class Plan:

    code: str
    price_id: str
    duration_days: int
    amount_pence: int


def plan_for_price(plans: Sequence[Plan], price_id: str) -> Plan:
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
