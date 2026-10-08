"""What a payment buys, and for how long.

b2c infers the plan from the pence amount paid, matched against a hardcoded
table, and raises ValueError("Invalid amount paid") on a miss — so a price
change, a currency difference or a Stripe coupon breaks the purchase after the
customer's card has been charged. The price id says what was bought.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.billing import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def test_a_plan_is_found_by_its_price_id() -> None:
    plan = domain.Plan(code="one_month", price_id="price_123", duration_days=30, amount_pence=2499)
    assert domain.plan_for_price([plan], "price_123") is plan


def test_an_unknown_price_id_is_refused_rather_than_guessed() -> None:
    """The customer has already paid at this point, so the failure has to be
    loud and recoverable rather than a silent grant of the wrong length."""
    with pytest.raises(domain.UnknownPlan):
        domain.plan_for_price([], "price_unseen")


def test_access_runs_from_payment_for_the_plans_duration() -> None:
    plan = domain.Plan(code="three_month", price_id="p", duration_days=90, amount_pence=6499)
    assert domain.access_window(plan, paid_at=NOW) == (NOW, NOW + timedelta(days=90))


def test_the_legacy_durations_are_preserved() -> None:
    """Oracle: `payment_service.PRICE_CONFIG` — 30, 90 and 180 days."""
    assert domain.DEFAULT_PLAN_DAYS == {"one_month": 30, "three_month": 90, "six_month": 180}


# --------------------------------------------------------------------------
# Webhook idempotency
# --------------------------------------------------------------------------


def test_an_unseen_event_is_processed() -> None:
    assert domain.should_process_event(seen=set(), event_id="evt_1")


def test_a_repeated_event_is_ignored() -> None:
    """Stripe retries until it gets a 2xx, and b2c returns 500 on failure to
    force exactly that — with no record of what it already did."""
    assert not domain.should_process_event(seen={"evt_1"}, event_id="evt_1")


def test_an_event_without_an_id_is_refused() -> None:
    with pytest.raises(domain.InvalidEvent):
        domain.should_process_event(seen=set(), event_id="")


# --------------------------------------------------------------------------
# Which events matter
# --------------------------------------------------------------------------


def test_only_completed_checkouts_grant_access() -> None:
    assert domain.grants_access("checkout.session.completed")


@pytest.mark.parametrize(
    "event_type",
    ["payment_intent.succeeded", "invoice.paid", "customer.subscription.created"],
)
def test_other_events_are_acknowledged_and_ignored(event_type: str) -> None:
    """Acknowledged, not errored: returning non-2xx would make Stripe retry an
    event we will never act on."""
    assert not domain.grants_access(event_type)


def test_a_referral_discount_is_named_after_its_full_price_plan() -> None:
    assert domain.referral_plan_code("sca_1m") == "sca_1m_referral"
    assert domain.is_referral_plan("sca_1m_referral")
    assert not domain.is_referral_plan("sca_1m")


@pytest.mark.parametrize("event_type", ["charge.refunded", "charge.dispute.created"])
def test_a_refund_or_a_dispute_withdraws_access(event_type: str) -> None:
    assert domain.withdraws_access(event_type)
    assert not domain.grants_access(event_type)


def test_only_a_full_refund_withdraws_access() -> None:
    assert domain.is_full_refund({"amount": 2249, "amount_refunded": 2249, "refunded": True})
    assert not domain.is_full_refund({"amount": 2249, "amount_refunded": 500, "refunded": False})
