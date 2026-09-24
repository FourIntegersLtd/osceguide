"""The streak arithmetic, pinned against `achievementsFromAttempts.ts`'s
original definition: a badge every three consecutive practice days.
"""

from __future__ import annotations

from datetime import date

from app.features.dashboard import service_achievements as sa


def d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_a_run_of_three_consecutive_days_is_one_badge() -> None:
    days = [d("2026-09-01"), d("2026-09-02"), d("2026-09-03")]
    longest = sa._longest_run(days)
    assert longest is not None
    assert longest.length == 3
    assert (longest.length // 3) == 1


def test_a_gap_breaks_the_run() -> None:
    days = [d("2026-09-01"), d("2026-09-02"), d("2026-09-05"), d("2026-09-06")]
    longest = sa._longest_run(days)
    assert longest is not None
    assert longest.length == 2
    # The first of the two equal-length runs wins, same as the TS original.
    assert longest.start_date == d("2026-09-01")


def test_no_days_is_no_streak() -> None:
    assert sa._longest_run([]) is None
    assert sa._current_run([], today=d("2026-09-24")) == 0


def test_the_current_run_survives_today_not_being_practised_yet() -> None:
    """Yesterday still counts as the streak continuing — today isn't over."""
    days = [d("2026-09-22"), d("2026-09-23")]
    assert sa._current_run(days, today=d("2026-09-24")) == 2


def test_the_current_run_dies_two_days_after_the_last_practice() -> None:
    days = [d("2026-09-20"), d("2026-09-21")]
    assert sa._current_run(days, today=d("2026-09-24")) == 0


def test_a_single_todays_attempt_is_a_streak_of_one() -> None:
    assert sa._current_run([d("2026-09-24")], today=d("2026-09-24")) == 1
