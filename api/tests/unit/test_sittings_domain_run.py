"""The run machine: what follows what, and how the clock behaves under a pause.

Pure rules, no database. This is the whole of "the circuit runs itself": every
scheduled transition and every override asks this module what the next step is
and when it ends, so a wrong answer here is a station that never starts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.sittings import domain, domain_alerts, domain_run
from app.features.sittings.domain import Break, Mode, Timing

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)

PLAIN = Timing(reading_minutes=3, simulation_minutes=10, break_minutes=5)
WITH_BREAK = Timing(
    reading_minutes=3, simulation_minutes=10, break_minutes=5, breaks=(Break(after_station=2),)
)


def at(phase: domain_run.RunPhase | None, index: int | None) -> domain_run.Position:
    return domain_run.Position(phase=phase, slot_index=index)


# --------------------------------------------------------------------------
# The sequence
# --------------------------------------------------------------------------


def test_a_fresh_circuit_starts_by_reading_the_first_station() -> None:
    step = domain_run.next_step(at(None, None), slot_count=3, timing=PLAIN)
    assert step == domain_run.Reading(slot_index=0)


def test_a_circuit_with_no_stations_is_finished_before_it_starts() -> None:
    assert domain_run.next_step(at(None, None), slot_count=0, timing=PLAIN) == domain_run.Finished()


def test_the_consultation_follows_the_reading_of_the_same_station() -> None:
    step = domain_run.next_step(at(domain_run.RunPhase.READING, 0), slot_count=3, timing=PLAIN)
    assert step == domain_run.Simulation(slot_index=0)


def test_the_next_station_follows_a_consultation() -> None:
    step = domain_run.next_step(at(domain_run.RunPhase.SIMULATION, 0), slot_count=3, timing=PLAIN)
    assert step == domain_run.Reading(slot_index=1)


def test_the_circuit_finishes_after_the_last_consultation() -> None:
    step = domain_run.next_step(at(domain_run.RunPhase.SIMULATION, 2), slot_count=3, timing=PLAIN)
    assert step == domain_run.Finished()


def test_a_redone_station_hands_on_to_the_first_station_not_yet_sat() -> None:
    """R-12: redoing station 0 from station 2 goes back to 2, not through 1 again."""
    step = domain_run.next_step(
        at(domain_run.RunPhase.SIMULATION, 0), slot_count=3, timing=PLAIN, done=frozenset({0, 1})
    )
    assert step == domain_run.Reading(slot_index=2)


# --------------------------------------------------------------------------
# Breaks
# --------------------------------------------------------------------------


def test_a_break_falls_after_the_station_that_names_it() -> None:
    """`after_station` is 1-based, so a break after station 2 follows slot index 1."""
    step = domain_run.next_step(at(domain_run.RunPhase.SIMULATION, 1), slot_count=4, timing=WITH_BREAK)
    assert step == domain_run.BreakStep(after_station=2)


def test_the_next_reading_follows_a_break() -> None:
    step = domain_run.next_step(at(domain_run.RunPhase.BREAK, 1), slot_count=4, timing=WITH_BREAK)
    assert step == domain_run.Reading(slot_index=2)


def test_a_break_after_the_last_station_is_not_taken() -> None:
    """There is nothing to come back to, so the circuit ends rather than waiting."""
    timing = Timing(
        reading_minutes=3, simulation_minutes=10, break_minutes=5, breaks=(Break(after_station=2),)
    )
    step = domain_run.next_step(at(domain_run.RunPhase.SIMULATION, 1), slot_count=2, timing=timing)
    assert step == domain_run.Finished()


def test_a_training_circuit_rotates_through_its_pairings_without_breaks() -> None:
    """Training composes its slots as pairings and `normalise_timing` gives it no breaks.

    One machine serves both modes: the difference is in the slots, not the walk.
    """
    timing = domain.normalise_timing({"breaks": [{"after_station": 1}]}, mode=Mode.TRAINING)
    assert timing.breaks == ()
    assert domain_run.next_step(at(domain_run.RunPhase.SIMULATION, 0), slot_count=3, timing=timing) == (
        domain_run.Reading(slot_index=1)
    )


# --------------------------------------------------------------------------
# The clock
# --------------------------------------------------------------------------


def test_each_step_runs_for_its_own_minutes() -> None:
    assert domain_run.step_window(domain_run.Reading(0), timing=PLAIN, now=NOW) == (
        NOW,
        NOW + timedelta(minutes=3),
    )
    assert domain_run.step_window(domain_run.Simulation(0), timing=PLAIN, now=NOW) == (
        NOW,
        NOW + timedelta(minutes=10),
    )
    assert domain_run.step_window(domain_run.BreakStep(1), timing=PLAIN, now=NOW) == (
        NOW,
        NOW + timedelta(minutes=5),
    )


def test_a_break_with_its_own_minutes_counts_down_that_long() -> None:
    timing = Timing(
        reading_minutes=3,
        simulation_minutes=10,
        break_minutes=5,
        breaks=(Break(after_station=2, minutes=15), Break(after_station=4)),
    )
    assert domain_run.step_window(domain_run.BreakStep(2), timing=timing, now=NOW) == (
        NOW,
        NOW + timedelta(minutes=15),
    )
    assert domain_run.step_window(domain_run.BreakStep(4), timing=timing, now=NOW) == (
        NOW,
        NOW + timedelta(minutes=5),
    )


def test_a_finished_circuit_has_no_window() -> None:
    with pytest.raises(domain.InvalidCircuit):
        domain_run.step_window(domain_run.Finished(), timing=PLAIN, now=NOW)


def test_a_step_with_no_time_is_refused() -> None:
    timing = Timing(reading_minutes=0, simulation_minutes=10, break_minutes=5)
    with pytest.raises(domain.InvalidCircuit):
        domain_run.step_window(domain_run.Reading(0), timing=timing, now=NOW)


def test_resuming_pushes_the_deadline_by_the_time_spent_paused() -> None:
    ends = NOW + timedelta(minutes=10)
    paused = NOW + timedelta(minutes=4)
    resumed = domain_run.resumed_deadline(ends, paused_at=paused, now=paused + timedelta(minutes=7))
    assert resumed == ends + timedelta(minutes=7)


def test_remaining_seconds_freeze_while_paused() -> None:
    """A candidate does not lose their consultation to a technical problem."""
    ends = NOW + timedelta(minutes=10)
    paused = NOW + timedelta(minutes=4)
    much_later = paused + timedelta(hours=2)
    assert domain_run.remaining_seconds(ends, paused_at=paused, now=much_later) == 6 * 60


def test_remaining_seconds_never_go_negative() -> None:
    ends = NOW + timedelta(minutes=10)
    assert domain_run.remaining_seconds(ends, paused_at=None, now=ends + timedelta(minutes=5)) == 0


def test_remaining_seconds_are_none_when_nothing_is_running() -> None:
    assert domain_run.remaining_seconds(None, paused_at=None, now=NOW) is None


def test_elapsed_seconds_exclude_the_time_spent_paused() -> None:
    started = NOW
    now = NOW + timedelta(minutes=10)
    assert domain_run.elapsed_seconds(started, paused_seconds=120, paused_at=None, now=now) == 8 * 60


def test_elapsed_seconds_stop_climbing_while_paused() -> None:
    started = NOW
    paused = NOW + timedelta(minutes=4)
    assert (
        domain_run.elapsed_seconds(
            started, paused_seconds=0, paused_at=paused, now=paused + timedelta(hours=1)
        )
        == 4 * 60
    )


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------


def test_pausing_a_paused_circuit_is_refused() -> None:
    with pytest.raises(domain_run.CircuitPaused):
        domain_run.ensure_not_paused(NOW)
    domain_run.ensure_not_paused(None)


def test_resuming_a_running_circuit_is_refused() -> None:
    with pytest.raises(domain_run.CircuitNotPaused):
        domain_run.ensure_paused(None)
    domain_run.ensure_paused(NOW)


@pytest.mark.parametrize("index", [-1, 3, 99])
def test_a_jump_outside_the_circuit_is_refused(index: int) -> None:
    with pytest.raises(domain.InvalidCircuit):
        domain_run.ensure_jump_target(index, slot_count=3, slot_status="scheduled", mode="exam")


def test_a_jump_to_a_real_station_is_allowed() -> None:
    domain_run.ensure_jump_target(2, slot_count=3, slot_status="scheduled", mode="exam")


@pytest.mark.parametrize("status", ["completed", "skipped"])
def test_an_exam_jump_to_a_finished_station_is_refused(status: str) -> None:
    with pytest.raises(domain.InvalidCircuit):
        domain_run.ensure_jump_target(1, slot_count=3, slot_status=status, mode="exam")


@pytest.mark.parametrize("status", ["completed", "skipped"])
def test_a_training_jump_back_to_a_finished_turn_is_allowed(status: str) -> None:
    """A trainee who was passed over, or wants another go, can be brought back in."""
    domain_run.ensure_jump_target(1, slot_count=3, slot_status=status, mode="training")


# --------------------------------------------------------------------------
# Alerts: what the exam-day board must not make somebody notice for themselves
# --------------------------------------------------------------------------


def test_a_consultation_with_no_patient_in_it_alerts() -> None:
    """The failure this exists for: the dispatch succeeded and no agent arrived."""
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.SIMULATION,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=10),
        paused_at=None,
        attempt_status="created",
        auto_advance=True,
        now=NOW + timedelta(seconds=45),
    )
    assert domain_alerts.NO_RUNNING_ATTEMPT in alerts


def test_a_consultation_that_has_only_just_started_is_given_a_moment() -> None:
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.SIMULATION,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=10),
        paused_at=None,
        attempt_status="created",
        auto_advance=True,
        now=NOW + timedelta(seconds=5),
    )
    assert domain_alerts.NO_RUNNING_ATTEMPT not in alerts


def test_a_failed_attempt_alerts() -> None:
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.SIMULATION,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=10),
        paused_at=None,
        attempt_status="failed",
        auto_advance=True,
        now=NOW + timedelta(seconds=5),
    )
    assert domain_alerts.ATTEMPT_FAILED in alerts


def test_an_overdue_phase_alerts() -> None:
    """The job worker is down, or a transition raised. Somebody must be told."""
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.READING,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=3),
        paused_at=None,
        attempt_status=None,
        auto_advance=True,
        now=NOW + timedelta(minutes=5),
    )
    assert domain_alerts.CLOCK_OVERDUE in alerts


def test_a_circuit_run_by_hand_is_never_overdue() -> None:
    """R-14: with auto-advance off the clock running out is the cue to advance, not a fault."""
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.READING,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=3),
        paused_at=None,
        attempt_status=None,
        auto_advance=False,
        now=NOW + timedelta(minutes=30),
    )
    assert alerts == []


def test_a_paused_circuit_is_not_overdue() -> None:
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.READING,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=3),
        paused_at=NOW + timedelta(minutes=1),
        attempt_status=None,
        auto_advance=True,
        now=NOW + timedelta(hours=1),
    )
    assert alerts == []


def test_a_reading_period_is_not_expected_to_have_a_patient() -> None:
    alerts = domain_alerts.alerts_for(
        phase=domain_run.RunPhase.READING,
        phase_started_at=NOW,
        phase_ends_at=NOW + timedelta(minutes=3),
        paused_at=None,
        attempt_status=None,
        auto_advance=True,
        now=NOW + timedelta(minutes=1),
    )
    assert alerts == []


# --- when a sitting is over (D-7) ------------------------------------------


def test_a_sitting_is_over_once_its_last_circuit_ends() -> None:
    assert domain_run.sitting_is_over([True, True])


def test_a_sitting_with_a_circuit_still_running_is_not_over() -> None:
    assert not domain_run.sitting_is_over([True, False])


def test_a_sitting_with_a_circuit_still_to_run_is_not_over() -> None:
    """A morning circuit finishing does not end an exam day with an afternoon one."""
    assert not domain_run.sitting_is_over([True, False])


def test_a_sitting_with_no_circuits_at_all_is_not_over() -> None:
    """It never started, so there is nothing to have finished."""
    assert not domain_run.sitting_is_over([])


def test_a_voice_fault_replaces_the_overdue_alert() -> None:
    """R-16: a late clock caused by LiveKit says so, rather than blaming the worker."""
    now = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
    alerts = domain_alerts.alerts_for(
        phase="reading",
        phase_started_at=now - timedelta(minutes=5),
        phase_ends_at=now - timedelta(minutes=2),
        paused_at=None,
        attempt_status=None,
        auto_advance=True,
        now=now,
        voice_fault=True,
    )

    assert alerts == ["voice_fault"]
