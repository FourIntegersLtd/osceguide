"""How a circuit walks itself from one station to the next.

A real examination runs on a bell, not on somebody remembering to press a
button: the station starts, the patient is already in the room, the bell goes,
everyone moves. This module is that bell as plain Python — given where a
circuit is, what comes next and how long it lasts.

Both modes use one machine: training has no breaks, so "rotate the group" and
"walk one candidate through twelve stations" are the same walk over different
slots.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.features.sittings.domain import InvalidCircuit, Timing


class RunPhase(StrEnum):
    """What a circuit is counting down.

    `BREAK` has no slot: it is the circuit resting between stations, so the
    clock lives on the circuit rather than on a slot.
    """

    READING = "reading"
    SIMULATION = "simulation"
    BREAK = "break"


@dataclass(frozen=True)
class Reading:
    """The candidate is reading the brief for this station."""

    slot_index: int


@dataclass(frozen=True)
class Simulation:
    """The patient is in the room and the consultation is running."""

    slot_index: int


@dataclass(frozen=True)
class BreakStep:
    """A scheduled rest. `after_station` is 1-based, as an examiner writes it."""

    after_station: int


@dataclass(frozen=True)
class Finished:
    """Every station has been sat."""


Step = Reading | Simulation | BreakStep | Finished


@dataclass(frozen=True)
class Position:
    """Where a circuit is now. Both fields are null before it has started."""

    phase: RunPhase | None
    slot_index: int | None


class CircuitPaused(Exception):
    """The clock is stopped, so this cannot happen yet."""


class CircuitNotPaused(Exception):
    """The clock is running, so there is nothing to resume."""


def next_step(position: Position, *, slot_count: int, timing: Timing) -> Step:
    """What follows where the circuit is now.

    The whole sequence, in one place, so the scheduled job and every override
    agree about what "next" means. Reading and its consultation belong to the
    same station; a break falls between two stations and never after the last,
    because there would be nothing to come back to.
    """
    if slot_count <= 0:
        return Finished()

    breaks = {entry.after_station for entry in timing.breaks}

    if position.phase is None or position.slot_index is None:
        return Reading(slot_index=0)

    index = position.slot_index

    if position.phase is RunPhase.READING:
        return Simulation(slot_index=index)

    if position.phase is RunPhase.BREAK:
        # A break is named by the station it follows, which is `index + 1`
        # in 1-based terms; the station it returns to is the next slot.
        return _reading_or_finished(index + 1, slot_count)

    # A consultation has ended.
    finished_station = index + 1
    if finished_station >= slot_count:
        return Finished()
    if finished_station in breaks:
        return BreakStep(after_station=finished_station)
    return Reading(slot_index=finished_station)


def _reading_or_finished(index: int, slot_count: int) -> Step:
    return Reading(slot_index=index) if index < slot_count else Finished()


def step_window(step: Step, *, timing: Timing, now: datetime) -> tuple[datetime, datetime]:
    """When a step that starts now ends.

    The deadline is server-side (D-6), written on the circuit so every screen
    reads the same value; it used to live in the supervisor's browser, lost on
    refresh.
    """
    minutes = _minutes_for(step, timing)
    if minutes <= 0:
        raise InvalidCircuit("A phase needs a positive duration.")
    return now, now + timedelta(minutes=minutes)


def _minutes_for(step: Step, timing: Timing) -> int:
    """How long `step` lasts, from the circuit's timing."""
    match step:
        case Reading():
            return timing.reading_minutes
        case Simulation():
            return timing.simulation_minutes
        case BreakStep():
            return timing.break_minutes
        case _:
            raise InvalidCircuit("A finished circuit is not counting anything down.")


def phase_of(step: Step) -> RunPhase | None:
    """Which phase `step` counts as, or None for `Finished`."""
    match step:
        case Reading():
            return RunPhase.READING
        case Simulation():
            return RunPhase.SIMULATION
        case BreakStep():
            return RunPhase.BREAK
        case _:
            return None


def resumed_deadline(phase_ends_at: datetime, *, paused_at: datetime, now: datetime) -> datetime:
    """The deadline after a pause: pushed out by exactly as long as it was stopped.

    A pause must not cost a candidate their consultation, and must not give
    them extra time either.
    """
    return phase_ends_at + (now - paused_at)


def remaining_seconds(
    phase_ends_at: datetime | None, *, paused_at: datetime | None, now: datetime
) -> int | None:
    """How long is left, computed here rather than in each screen.

    While paused, the answer is frozen at whatever was left when the clock
    stopped — otherwise a paused examination would visibly run out on the board.
    """
    if phase_ends_at is None:
        return None
    reference = paused_at or now
    return max(0, int((phase_ends_at - reference).total_seconds()))


def elapsed_seconds(
    phase_started_at: datetime | None,
    *,
    paused_seconds: int,
    paused_at: datetime | None,
    now: datetime,
) -> int | None:
    """Time actually spent in this phase, with every pause taken back out."""
    if phase_started_at is None:
        return None
    reference = paused_at or now
    return max(0, int((reference - phase_started_at).total_seconds()) - paused_seconds)


def ensure_not_paused(paused_at: datetime | None) -> None:
    """Refuse to pause a clock that is already stopped."""
    if paused_at is not None:
        raise CircuitPaused("The clock is already stopped.")


def ensure_paused(paused_at: datetime | None) -> None:
    """Refuse to resume a clock that is running."""
    if paused_at is None:
        raise CircuitNotPaused("The clock is running; there is nothing to resume.")


def ensure_jump_target(slot_index: int, *, slot_count: int) -> None:
    """Refuse to jump to a station that is not on this circuit."""
    if not 0 <= slot_index < slot_count:
        raise InvalidCircuit("That station is not on this circuit.")


def sitting_is_over(circuit_ended: Iterable[bool]) -> bool:
    """Whether a sitting has nothing left to run (D-7).

    True only when every circuit has ended, not just the last running one — a
    sitting was previously left `in_progress` forever once set by the first
    circuit, so a finished exam day kept reading as running. An unstarted
    circuit keeps its sitting open, since "not yet" and "never will be" look
    the same; staff end it outright to close the sitting. No circuits at all
    means the sitting is not over — it never began.
    """
    ended = list(circuit_ended)
    return bool(ended) and all(ended)
