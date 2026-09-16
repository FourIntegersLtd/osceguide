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


# --------------------------------------------------------------------------
# Reference ids
# --------------------------------------------------------------------------


def test_a_reference_id_is_partner_and_exam() -> None:
    assert domain.format_ref_id("bmj", "sca") == "bmj-sca"


def test_an_unknown_partner_cannot_be_formatted() -> None:
    with pytest.raises(domain.UnknownPartner):
        domain.format_ref_id("someone-else", "sca")


def test_an_exam_outside_the_pilot_cannot_be_formatted() -> None:
    """Oracle: `PILOT_EXAMS` excludes casc."""
    with pytest.raises(domain.ExamNotInPilot):
        domain.format_ref_id("bmj", "casc")


@pytest.mark.parametrize(("ref_id", "exam"), [("bmj-sca", "sca"), ("bmj-plab", "plab")])
def test_an_exam_is_parsed_back_out(ref_id: str, exam: str) -> None:
    assert domain.parse_ref_id(ref_id) == ("bmj", exam)


@pytest.mark.parametrize("ref_id", ["", "nonsense", "bmj", "other-sca", "bmj-casc"])
def test_anything_unrecognised_parses_to_nothing(ref_id: str) -> None:
    """Never guessed. A misattributed signup is money owed to the wrong party."""
    assert domain.parse_ref_id(ref_id) is None


def test_a_landing_path_identifies_the_exam() -> None:
    assert domain.exam_from_landing_path("/exams/plab") == "plab"
    assert domain.exam_from_landing_path("/exams/casc") is None
    assert domain.exam_from_landing_path("/pricing") is None


# --------------------------------------------------------------------------
# Attribution window
# --------------------------------------------------------------------------


def test_a_recent_arrival_attributes_a_signup() -> None:
    assert domain.attributes(arrived_at=NOW - timedelta(days=30), signed_up_at=NOW)


def test_an_arrival_outside_the_window_does_not() -> None:
    """Oracle: a 90-day cookie. Past that the signup is not the partner's."""
    assert not domain.attributes(
        arrived_at=NOW - domain.ATTRIBUTION_WINDOW - timedelta(days=1), signed_up_at=NOW
    )


def test_the_boundary_attributes() -> None:
    assert domain.attributes(arrived_at=NOW - domain.ATTRIBUTION_WINDOW, signed_up_at=NOW)


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
