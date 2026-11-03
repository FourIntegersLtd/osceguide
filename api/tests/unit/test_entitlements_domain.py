"""May this person attempt this exam now?

One predicate with several sources. The free-trial rule is ported verbatim from
`b2c auth_service.check_subscription`; if it changes, somebody's trial changes,
so it changes deliberately or not at all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.entitlements import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def grant(source: str = "purchase", *, ends_at: datetime | None = None, revoked: bool = False):  # type: ignore[no-untyped-def]
    return domain.Grant(
        source=source,
        starts_at=NOW - timedelta(days=1),
        ends_at=ends_at,
        revoked_at=NOW if revoked else None,
    )


# --------------------------------------------------------------------------
# Grants
# --------------------------------------------------------------------------


def test_an_unexpired_purchase_permits_an_attempt() -> None:
    assert domain.decide([grant(ends_at=NOW + timedelta(days=30))], now=NOW).allowed


def test_a_perpetual_grant_has_no_end() -> None:
    assert domain.decide([grant(ends_at=None)], now=NOW).allowed


def test_an_expired_grant_does_not() -> None:
    decision = domain.decide([grant(ends_at=NOW - timedelta(days=1))], now=NOW)
    assert not decision.allowed
    assert decision.reason == "expired"


def test_a_revoked_grant_does_not_count_even_if_unexpired() -> None:
    decision = domain.decide([grant(ends_at=NOW + timedelta(days=30), revoked=True)], now=NOW)
    assert not decision.allowed


def test_a_grant_that_has_not_started_does_not_count() -> None:
    future = domain.Grant(source="org_grant", starts_at=NOW + timedelta(days=1), ends_at=None)
    assert not domain.decide([future], now=NOW).allowed


@pytest.mark.parametrize("source", ["purchase", "org_grant", "trial", "sso_tenant", "admin"])
def test_every_source_resolves_through_the_same_predicate(source: str) -> None:
    """A consumer who bought access and a trainee an institution granted it to
    reach the same answer by the same route."""
    assert domain.decide([grant(source, ends_at=NOW + timedelta(days=1))], now=NOW).allowed


def test_one_live_grant_is_enough() -> None:
    grants = [grant(ends_at=NOW - timedelta(days=5)), grant("org_grant", ends_at=NOW + timedelta(days=5))]
    assert domain.decide(grants, now=NOW).allowed


def test_with_no_grants_the_reason_says_so() -> None:
    decision = domain.decide([], now=NOW)
    assert not decision.allowed
    assert decision.reason == "no_entitlement"


# --------------------------------------------------------------------------
# The free trial, ported verbatim
# --------------------------------------------------------------------------


def trial(*, set_stations: int = 0, completed: int = 0, age_days: int = 0, this_station: int | None = None):  # type: ignore[no-untyped-def]
    return domain.TrialState(
        set_station_count=set_stations,
        completed_station_count=completed,
        trial_started_at=NOW - timedelta(days=age_days),
        completed_on_this_station=this_station,
    )


@pytest.mark.parametrize("finished", [0, 1, 2])
def test_a_trial_station_can_be_retried_after_all_three_are_used(finished: int) -> None:
    """Three stations, three attempts each: finishing all three stations still leaves their retries."""
    assert domain.trial_available(trial(set_stations=3, completed=3, this_station=finished), now=NOW)


def test_a_trial_station_finished_three_times_is_used_up() -> None:
    assert not domain.trial_available(trial(completed=1, this_station=3), now=NOW)


def test_a_fourth_station_is_refused() -> None:
    assert not domain.trial_available(trial(completed=3, this_station=None), now=NOW)


def test_a_retry_after_fourteen_days_is_refused() -> None:
    assert not domain.trial_available(trial(age_days=15, this_station=0), now=NOW)


def test_a_new_account_with_no_activity_is_inside_the_trial() -> None:
    assert domain.trial_available(trial(), now=NOW)


@pytest.mark.parametrize("count", [3, 4, 10])
def test_three_set_stations_exhausts_the_trial(count: int) -> None:
    """Oracle: `total_mock_stations >= ALLOWED_STATION_ATTEMPTS`, which is 3."""
    assert not domain.trial_available(trial(set_stations=count), now=NOW)


@pytest.mark.parametrize("count", [3, 4, 10])
def test_three_completed_stations_exhausts_the_trial(count: int) -> None:
    """Oracle: `completed_station_count >= ALLOWED_STATION_ATTEMPTS`."""
    assert not domain.trial_available(trial(completed=count), now=NOW)


def test_two_of_each_does_not_exhaust_it() -> None:
    """The legacy rule compares each count separately rather than their sum."""
    assert domain.trial_available(trial(set_stations=2, completed=2), now=NOW)


def test_an_account_older_than_fourteen_days_has_no_trial_left() -> None:
    """Oracle: `created_at < now - timedelta(days=14)`."""
    assert not domain.trial_available(trial(age_days=15), now=NOW)


def test_exactly_fourteen_days_is_still_inside_the_trial() -> None:
    """Strictly older than, per the legacy comparison — the boundary matters
    because it decides whether someone can practise today."""
    assert domain.trial_available(trial(age_days=14), now=NOW)


def test_the_trial_is_only_consulted_when_nothing_is_granted() -> None:
    decision = domain.decide([], now=NOW, trial=trial(), exam_code="sca")
    assert decision.allowed
    assert decision.source == "trial"


def test_a_trial_past_its_fourteen_days_is_refused_as_expired() -> None:
    decision = domain.decide([], now=NOW, trial=trial(age_days=30))
    assert not decision.allowed
    assert decision.reason == "trial_expired"


def test_a_trial_inside_its_days_with_its_stations_used_is_refused_as_exhausted() -> None:
    decision = domain.decide([], now=NOW, trial=trial(set_stations=3))
    assert not decision.allowed
    assert decision.reason == "trial_exhausted"


def test_a_lapsed_subscriber_past_the_trial_is_told_expired_not_trial_exhausted() -> None:
    lapsed = grant(ends_at=NOW - timedelta(days=1))
    decision = domain.decide([lapsed], now=NOW, trial=trial(age_days=30))
    assert not decision.allowed
    assert decision.reason == "expired"


def test_somebody_whose_only_purchase_was_refunded_is_not_told_expired() -> None:
    decision = domain.decide([grant(revoked=True)], now=NOW, trial=trial(age_days=30))
    assert decision.reason == "trial_expired"
    assert domain.decide([grant(revoked=True)], now=NOW).reason == "no_entitlement"


@pytest.mark.parametrize(
    ("set_stations", "completed", "age_days", "left"),
    [(0, 0, 0, 3), (1, 0, 0, 2), (1, 2, 0, 1), (3, 3, 0, 0), (0, 0, 15, 0)],
)
def test_the_trial_stations_left_are_the_larger_counter_taken_from_three(
    set_stations: int, completed: int, age_days: int, left: int
) -> None:
    """What the setup screen caps a free session at; a closed trial window leaves none."""
    state = trial(set_stations=set_stations, completed=completed, age_days=age_days)
    assert domain.trial_stations_left(state, now=NOW) == left
