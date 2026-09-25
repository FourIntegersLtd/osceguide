"""Claiming a peer's offered slot.

Ported from `b2c firestore_service.claim_marketplace_availability_post:836-868`,
which is a real transaction because two people press the button at once.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.marketplace import domain

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
OWNER = "owner-1"
CLAIMER = "claimer-1"


def post(status: str = "available", owner: str = OWNER, starts_in_hours: int = 24):  # type: ignore[no-untyped-def]
    return domain.PostState(status=status, owner_id=owner, starts_at=NOW + timedelta(hours=starts_in_hours))


def test_an_available_post_can_be_claimed() -> None:
    domain.ensure_claimable(post(), claimer_id=CLAIMER, now=NOW)


@pytest.mark.parametrize("status", ["claimed", "cancelled", "completed"])
def test_a_post_that_is_not_available_cannot_be_claimed(status: str) -> None:
    """Oracle: the status check inside the transaction."""
    with pytest.raises(domain.PostUnavailable):
        domain.ensure_claimable(post(status=status), claimer_id=CLAIMER, now=NOW)


def test_you_cannot_claim_your_own_post() -> None:
    """Oracle: "You cannot claim your own post"."""
    with pytest.raises(domain.CannotClaimOwnPost):
        domain.ensure_claimable(post(), claimer_id=OWNER, now=NOW)


def test_a_post_in_the_past_cannot_be_claimed() -> None:
    """Not in the legacy check, and it should be: claiming a session that
    started yesterday books nobody into anything."""
    with pytest.raises(domain.PostUnavailable):
        domain.ensure_claimable(post(starts_in_hours=-1), claimer_id=CLAIMER, now=NOW)


# --------------------------------------------------------------------------
# Cancelling
# --------------------------------------------------------------------------


def test_an_owner_may_cancel_their_own_post() -> None:
    domain.ensure_cancellable(post(), actor_id=OWNER)


def test_someone_else_may_not_cancel_it() -> None:
    with pytest.raises(domain.NotYours):
        domain.ensure_cancellable(post(), actor_id=CLAIMER)


def test_a_completed_post_cannot_be_cancelled() -> None:
    with pytest.raises(domain.PostUnavailable):
        domain.ensure_cancellable(post(status="completed"), actor_id=OWNER)


# --------------------------------------------------------------------------
# Joining
# --------------------------------------------------------------------------


def test_both_parties_may_join_a_claimed_session() -> None:
    claimed = domain.SessionState(owner_id=OWNER, claimer_id=CLAIMER, starts_at=NOW, status="scheduled")
    assert domain.may_join(claimed, user_id=OWNER)
    assert domain.may_join(claimed, user_id=CLAIMER)


def test_nobody_else_may_join() -> None:
    claimed = domain.SessionState(owner_id=OWNER, claimer_id=CLAIMER, starts_at=NOW, status="scheduled")
    assert not domain.may_join(claimed, user_id="stranger")


def booked(status: str = "scheduled") -> domain.SessionState:
    return domain.SessionState(owner_id=OWNER, claimer_id=CLAIMER, starts_at=NOW, status=status)


def test_a_session_opens_twenty_minutes_before_it_starts() -> None:
    domain.ensure_joinable(booked(), now=NOW - timedelta(minutes=20))
    with pytest.raises(domain.SessionNotJoinable, match="not opened yet"):
        domain.ensure_joinable(booked(), now=NOW - timedelta(minutes=21))


def test_a_session_closes_an_hour_after_it_starts() -> None:
    domain.ensure_joinable(booked("active"), now=NOW + timedelta(minutes=60))
    with pytest.raises(domain.SessionNotJoinable, match="expired"):
        domain.ensure_joinable(booked("active"), now=NOW + timedelta(minutes=61))


def test_a_cancelled_session_cannot_be_joined_even_on_time() -> None:
    with pytest.raises(domain.SessionNotJoinable, match="cancelled"):
        domain.ensure_joinable(booked("cancelled"), now=NOW)
