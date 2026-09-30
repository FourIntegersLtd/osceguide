"""Attributing a signup to the partner who sent it.

Ported from `b2c partner_attribution_constants.py`. The stakes are commercial:
these numbers decide what a partner is owed, so the parsing has to be exact and
an unrecognised value must never be quietly attributed to somebody.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.growth import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

# Which exams are in the pilot is a flag on each exam row now, so the caller
# supplies the set. These stand in for three exams an admin has flagged.
PILOT = ("sca", "plab", "ortho")


# --------------------------------------------------------------------------
# Reference ids
# --------------------------------------------------------------------------


def test_a_reference_id_is_partner_and_exam() -> None:
    assert domain.format_ref_id("bmj", "sca", pilot_exams=PILOT) == "bmj-sca"


def test_an_unknown_partner_cannot_be_formatted() -> None:
    with pytest.raises(domain.UnknownPartner):
        domain.format_ref_id("someone-else", "sca", pilot_exams=PILOT)


def test_an_exam_outside_the_pilot_cannot_be_formatted() -> None:
    with pytest.raises(domain.ExamNotInPilot):
        domain.format_ref_id("bmj", "casc", pilot_exams=PILOT)


def test_the_pilot_is_whatever_the_caller_was_told_it_is() -> None:
    """It was a tuple of three codes here, so adding one was a code change."""
    assert domain.format_ref_id("bmj", "casc", pilot_exams=("casc",)) == "bmj-casc"
    assert domain.parse_ref_id("bmj-sca", pilot_exams=("casc",)) is None


@pytest.mark.parametrize(("ref_id", "exam"), [("bmj-sca", "sca"), ("bmj-plab", "plab")])
def test_an_exam_is_parsed_back_out(ref_id: str, exam: str) -> None:
    assert domain.parse_ref_id(ref_id, pilot_exams=PILOT) == ("bmj", exam)


@pytest.mark.parametrize("ref_id", ["", "nonsense", "bmj", "other-sca", "bmj-casc"])
def test_anything_unrecognised_parses_to_nothing(ref_id: str) -> None:
    """Never guessed. A misattributed signup is money owed to the wrong party."""
    assert domain.parse_ref_id(ref_id, pilot_exams=PILOT) is None


def test_a_landing_path_identifies_the_exam() -> None:
    assert domain.exam_from_landing_path("/exams/plab", pilot_exams=PILOT) == "plab"
    assert domain.exam_from_landing_path("/exams/casc", pilot_exams=PILOT) is None
    assert domain.exam_from_landing_path("/pricing", pilot_exams=PILOT) is None


# --------------------------------------------------------------------------
# Attribution
# --------------------------------------------------------------------------


def test_a_recent_arrival_attributes_a_signup() -> None:
    assert domain.attributes(arrived_at=NOW - timedelta(days=30), signed_up_at=NOW)


def test_an_old_arrival_still_attributes() -> None:
    """No window: once a partner's link is clicked, that partner is credited."""
    assert domain.attributes(arrived_at=NOW - timedelta(days=91), signed_up_at=NOW)
    assert domain.attributes(arrived_at=NOW - timedelta(days=365), signed_up_at=NOW)


def test_an_arrival_at_the_moment_of_signup_attributes() -> None:
    assert domain.attributes(arrived_at=NOW, signed_up_at=NOW)


def test_an_arrival_after_the_signup_does_not_attribute() -> None:
    """Somebody arriving via a partner link after they signed up was not sent
    by that partner."""
    assert not domain.attributes(arrived_at=NOW, signed_up_at=NOW - timedelta(days=1))


# --------------------------------------------------------------------------
# The funnel
# --------------------------------------------------------------------------


def test_the_funnel_counts_each_stage() -> None:
    funnel = domain.funnel(arrivals=100, signups=20, purchases=5)
    assert (funnel.arrivals, funnel.signups, funnel.purchases) == (100, 20, 5)


def test_conversion_is_a_share_of_the_stage_before() -> None:
    funnel = domain.funnel(arrivals=100, signups=20, purchases=5)
    assert funnel.signup_rate == pytest.approx(0.2)
    assert funnel.purchase_rate == pytest.approx(0.25)


def test_an_empty_funnel_does_not_divide_by_zero() -> None:
    funnel = domain.funnel(arrivals=0, signups=0, purchases=0)
    assert funnel.signup_rate == 0.0
    assert funnel.purchase_rate == 0.0


# --- referral rewards -------------------------------------------------------


@pytest.mark.parametrize(
    ("plan_duration_days", "reward_pence"),
    [(30, 250), (90, 500), (180, 500)],
)
def test_a_referrer_earns_what_b2c_paid_for_each_plan_length(
    plan_duration_days: int, reward_pence: int
) -> None:
    """b2c paid £2.50 for a one-month purchase and £5 for three or six months."""
    assert domain.referral_reward_pence(plan_duration_days) == reward_pence
