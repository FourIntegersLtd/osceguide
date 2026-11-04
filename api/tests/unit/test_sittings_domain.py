"""Circuit rules, ported from b2b as the oracle.

Sources: `slot_builder.py` (C1, C2), `integrity.py:153-168` (C3),
`circuit_timing.py` (C9), `circuit_control.py:173` (C7), `:321` (C8).
These decide what a supervisor can do mid-examination, so they are ported
rather than reinvented.
"""

from __future__ import annotations

import pytest

from app.features.sittings import domain
from app.features.sittings.domain import Mode

# --------------------------------------------------------------------------
# Building slots
# --------------------------------------------------------------------------


def test_an_exam_circuit_is_one_trainee_through_every_station() -> None:
    slots = domain.build_slots(Mode.EXAM, trainee_user_ids=["t1"], station_version_ids=["s1", "s2", "s3"])
    assert [s.station_version_id for s in slots] == ["s1", "s2", "s3"]
    assert {s.trainee_user_id for s in slots} == {"t1"}


def test_an_exam_circuit_refuses_more_than_one_trainee() -> None:
    """Oracle: slot_builder. An exam is one candidate's sitting."""
    with pytest.raises(domain.InvalidCircuit):
        domain.build_slots(Mode.EXAM, trainee_user_ids=["t1", "t2"], station_version_ids=["s1"])


def test_an_exam_circuit_is_capped_at_twelve_stations() -> None:
    """Oracle: `EXAM_MAX_STATIONS = 12`."""
    with pytest.raises(domain.InvalidCircuit):
        domain.build_slots(
            Mode.EXAM, trainee_user_ids=["t1"], station_version_ids=[f"s{i}" for i in range(13)]
        )


def test_a_training_circuit_pairs_each_trainee_with_one_station() -> None:
    """Oracle: the positional zip. Trainee i takes station i, and they rotate."""
    slots = domain.build_slots(Mode.TRAINING, trainee_user_ids=["a", "b"], station_version_ids=["s1", "s2"])
    assert [(s.trainee_user_id, s.station_version_id) for s in slots] == [("a", "s1"), ("b", "s2")]


def test_a_training_circuit_needs_matching_counts() -> None:
    with pytest.raises(domain.InvalidCircuit):
        domain.build_slots(Mode.TRAINING, trainee_user_ids=["a", "b"], station_version_ids=["s1"])


def test_a_circuit_with_no_stations_is_refused() -> None:
    with pytest.raises(domain.InvalidCircuit):
        domain.build_slots(Mode.TRAINING, trainee_user_ids=[], station_version_ids=[])


def test_slots_are_numbered_from_zero_in_order() -> None:
    slots = domain.build_slots(Mode.EXAM, trainee_user_ids=["t1"], station_version_ids=["s1", "s2"])
    assert [s.index for s in slots] == [0, 1]


# --------------------------------------------------------------------------
# Editing a live circuit
# --------------------------------------------------------------------------


def test_a_circuit_may_be_edited_before_it_starts() -> None:
    domain.ensure_editable(domain.CircuitState(active_slot_id=None, has_feedback=False))


def test_a_circuit_with_a_live_slot_is_locked() -> None:
    """Oracle: integrity.py. Rebuilding slots mid-station would delete the one
    somebody is sitting."""
    with pytest.raises(domain.CircuitLocked):
        domain.ensure_editable(domain.CircuitState(active_slot_id="slot-1", has_feedback=False))


def test_a_circuit_with_feedback_is_locked() -> None:
    with pytest.raises(domain.CircuitLocked):
        domain.ensure_editable(domain.CircuitState(active_slot_id=None, has_feedback=True))


def test_force_overrides_the_lock() -> None:
    """Kept because b2b has it and supervisors rely on it when a session goes
    wrong mid-circuit."""
    domain.ensure_editable(domain.CircuitState(active_slot_id="slot-1", has_feedback=True), force=True)


# --------------------------------------------------------------------------
# Running a circuit
# --------------------------------------------------------------------------


def test_appending_trainees_is_training_only() -> None:
    """Oracle: circuit_service.py:321."""
    domain.ensure_can_append_trainees(Mode.TRAINING)
    with pytest.raises(domain.NotPermittedInMode):
        domain.ensure_can_append_trainees(Mode.EXAM)


def test_a_finished_circuit_cannot_be_started() -> None:
    domain.ensure_startable(domain.CircuitState(active_slot_id=None, has_feedback=False))
    domain.ensure_startable(domain.CircuitState(active_slot_id="slot", has_feedback=False, started=True))
    with pytest.raises(domain.CircuitAlreadyEnded):
        domain.ensure_startable(domain.CircuitState(active_slot_id=None, has_feedback=False, ended=True))


def test_a_running_circuit_says_it_has_started() -> None:
    """R-3: the caller reads `started` to make a second Start a no-op, not a restart."""
    assert domain.CircuitState(active_slot_id=None, has_feedback=False).started is False
    assert domain.CircuitState(active_slot_id="slot", has_feedback=False, started=True).started is True


def test_only_one_slot_is_active_at_a_time() -> None:
    """C4 is enforced by the row lock and `ensure_live`, not by a pure function.

    There used to be a `next_active_slot(state, slot_id)` here that returned
    its argument, and a test asserting exactly that. It read like the
    invariant and proved nothing — the real guarantee is that the circuit row
    is held for the read-modify-write, which
    `tests/repository/test_circuit_switch_race.py` proves against Postgres.
    """
    state = domain.CircuitState(active_slot_id="slot-1", has_feedback=False)
    assert domain.edit_block(state) == "consultation_in_progress"


# --------------------------------------------------------------------------
# Timing
# --------------------------------------------------------------------------


def test_timing_defaults_match_the_legacy_values() -> None:
    """Oracle: circuit_timing.py — 3 minutes reading, 10 simulation."""
    timing = domain.normalise_timing({})
    assert timing.reading_minutes == 3
    assert timing.simulation_minutes == 10


@pytest.mark.parametrize(("given", "expected"), [(0, 1), (31, 30), (15, 15)])
def test_reading_minutes_are_clamped(given: int, expected: int) -> None:
    assert domain.normalise_timing({"reading_minutes": given}).reading_minutes == expected


@pytest.mark.parametrize(("given", "expected"), [(0, 1), (181, 180), (20, 20)])
def test_simulation_minutes_are_clamped(given: int, expected: int) -> None:
    assert domain.normalise_timing({"simulation_minutes": given}).simulation_minutes == expected


def test_the_legacy_station_minutes_key_is_still_accepted() -> None:
    """Oracle: circuit_timing.py:40. Existing circuits carry this spelling."""
    assert domain.normalise_timing({"station_minutes": 12}).simulation_minutes == 12


def test_breaks_are_exam_only() -> None:
    """Oracle: circuit_timing.py:64."""
    timing = domain.normalise_timing({"breaks": [{"after_station": 1}]}, mode=Mode.TRAINING)
    assert timing.breaks == ()


def test_a_break_has_a_length_of_its_own() -> None:
    """A break used to be a position with no duration, so nothing could count it down."""
    assert domain.normalise_timing({}).break_minutes == 5
    assert domain.normalise_timing({"break_minutes": 12}).break_minutes == 12


@pytest.mark.parametrize(("given", "expected"), [(0, 1), (61, 60), (8, 8)])
def test_break_minutes_are_clamped(given: int, expected: int) -> None:
    assert domain.normalise_timing({"break_minutes": given}).break_minutes == expected


def test_breaks_are_clamped_to_the_station_count_and_deduplicated() -> None:
    timing = domain.normalise_timing(
        {"breaks": [{"after_station": 5}, {"after_station": 1}, {"after_station": 1}, {"after_station": 0}]},
        mode=Mode.EXAM,
        station_count=3,
    )
    assert [b.after_station for b in timing.breaks] == [1, 2]


def test_a_break_keeps_its_own_minutes_and_clamps_them() -> None:
    timing = domain.normalise_timing(
        {
            "break_minutes": 5,
            "breaks": [
                {"after_station": 1, "minutes": 15},
                {"after_station": 2, "minutes": 99},
                {"after_station": 3},
            ],
        },
        mode=Mode.EXAM,
        station_count=4,
    )
    assert [b.minutes for b in timing.breaks] == [15, 60, None]
    assert [timing.minutes_after(n) for n in (1, 2, 3)] == [15, 60, 5]


def test_a_circuit_that_has_ended_is_no_longer_live() -> None:
    """Guards the moment after starting: is this still running?

    A switch that lands on an ended circuit leaves it showing a candidate
    consulting in a room already torn down.
    """
    with pytest.raises(domain.CircuitAlreadyEnded):
        domain.ensure_live(domain.CircuitState(active_slot_id=None, has_feedback=False, ended=True))


def test_a_running_circuit_is_live() -> None:
    domain.ensure_live(domain.CircuitState(active_slot_id="slot-1", has_feedback=False))
