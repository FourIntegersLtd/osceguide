"""A reusable practice set: what b2c calls a mock.

Kept separate from a circuit on purpose. A set is re-attemptable and locks when
a subscription lapses; a circuit slot is one-shot and scheduled. Collapsing them
would give a slot an attempt counter and a lock flag, which is b2b's mess in
reverse.
"""

from __future__ import annotations

import pytest

from app.features.station_sets import domain


def entry(attempts: int = 0, *, debriefs: int = 0) -> domain.EntryState:
    return domain.EntryState(attempts=attempts, debrief_attempts=debriefs)


def test_a_fresh_entry_can_be_attempted() -> None:
    domain.ensure_attemptable(entry(), limit=3, locked=False)


def test_the_per_station_attempt_limit_is_enforced() -> None:
    """Oracle: `exams.station_attempt_limit`, 3 in b2c."""
    with pytest.raises(domain.AttemptLimitReached):
        domain.ensure_attemptable(entry(attempts=3), limit=3, locked=False)


def test_a_locked_set_refuses_new_attempts() -> None:
    """b2c locks a set when the subscription lapses rather than deleting it, so
    the work stays visible and comes back on renewal."""
    with pytest.raises(domain.SetLocked):
        domain.ensure_attemptable(entry(), limit=3, locked=True)


def test_a_limit_of_zero_means_unlimited() -> None:
    domain.ensure_attemptable(entry(attempts=99), limit=0, locked=False)


def test_a_debrief_needs_a_completed_attempt() -> None:
    """There is nothing to debrief about otherwise."""
    with pytest.raises(domain.NothingToDebrief):
        domain.ensure_debriefable(entry(attempts=0), limit=3)


def test_a_debrief_is_allowed_after_an_attempt() -> None:
    domain.ensure_debriefable(entry(attempts=1), limit=3)


def test_debriefs_have_their_own_limit() -> None:
    with pytest.raises(domain.AttemptLimitReached):
        domain.ensure_debriefable(entry(attempts=3, debriefs=3), limit=3)


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------


def test_a_set_is_complete_when_every_entry_has_an_attempt() -> None:
    assert domain.set_complete([entry(attempts=1), entry(attempts=2)])


def test_a_set_with_an_untouched_entry_is_not_complete() -> None:
    assert not domain.set_complete([entry(attempts=1), entry()])


def test_an_empty_set_is_not_complete() -> None:
    """Otherwise a set created and never populated reports itself finished."""
    assert not domain.set_complete([])


def test_progress_counts_entries_attempted() -> None:
    assert domain.progress([entry(attempts=1), entry(), entry(attempts=4)]) == (2, 3)
