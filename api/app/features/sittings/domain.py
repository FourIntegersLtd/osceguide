"""How a sitting is built and run.

A **sitting** is a scheduled event an organisation holds. It contains
**circuits**, and a circuit contains **slots** — one trainee at one station.
Two modes behave differently enough to be worth naming:

- `training`: several trainees rotate through several stations together, one
  active at a time, driven by a supervisor.
- `exam`: one candidate works through every station of their own circuit,
  starting each themselves.

Ported from b2b, which is what currently runs examinations. These rules decide
what a supervisor can do in the middle of one, so they are carried over rather
than reinvented.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

# Oracle: `EXAM_MAX_STATIONS` in b2b's slot_builder.
EXAM_MAX_STATIONS = 12

DEFAULT_READING_MINUTES = 3
DEFAULT_SIMULATION_MINUTES = 10
READING_BOUNDS = (1, 30)
SIMULATION_BOUNDS = (1, 180)


class Mode(StrEnum):
    TRAINING = "training"
    EXAM = "exam"


class InvalidCircuit(Exception):
    pass


class CircuitLocked(Exception):
    pass


class CircuitAlreadyEnded(Exception):
    pass


class NotPermittedInMode(Exception):
    pass


@dataclass(frozen=True)
class PlannedSlot:
    index: int
    trainee: str
    station: str


@dataclass(frozen=True)
class CircuitState:
    active_slot_id: str | None
    has_feedback: bool
    ended: bool = False


@dataclass(frozen=True)
class Break:
    after_station: int


@dataclass(frozen=True)
class Timing:
    reading_minutes: int
    simulation_minutes: int
    breaks: tuple[Break, ...] = ()


class Phase(StrEnum):
    """Where a slot is in its station: reading the brief, or in the consultation."""

    READING = "reading"
    SIMULATION = "simulation"


def phase_window(
    phase: Phase, *, reading_minutes: int, simulation_minutes: int, now: datetime
) -> tuple[datetime, datetime]:
    """When a phase that starts now ends (D-6).

    The clock is the server's: the phase and its end are written on the slot
    when a supervisor moves the turn or dispatches the patient, and every
    screen reads the same deadline. It used to be the supervisor's browser,
    lost on refresh and never shown to the candidate.
    """
    minutes = reading_minutes if phase is Phase.READING else simulation_minutes
    if minutes <= 0:
        raise InvalidCircuit("A phase needs a positive duration.")
    return now, now + timedelta(minutes=minutes)


def build_slots(mode: Mode, *, trainees: Sequence[str], stations: Sequence[str]) -> list[PlannedSlot]:
    """The slots a circuit starts with.

    Exam and training compose differently because they mean different things: a
    candidate sits every station, whereas a training group rotates so that each
    person is at a different station at the same time.
    """
    if not stations:
        raise InvalidCircuit("A circuit needs at least one station.")

    if mode is Mode.EXAM:
        if len(trainees) != 1:
            raise InvalidCircuit("An exam circuit is one candidate's sitting.")
        if len(stations) > EXAM_MAX_STATIONS:
            raise InvalidCircuit(f"An exam circuit takes at most {EXAM_MAX_STATIONS} stations.")
        return [PlannedSlot(i, trainees[0], station) for i, station in enumerate(stations)]

    if len(trainees) != len(stations):
        raise InvalidCircuit(
            "A training circuit needs one station per trainee, so everyone starts somewhere."
        )
    return [
        PlannedSlot(i, trainee, station)
        for i, (trainee, station) in enumerate(zip(trainees, stations, strict=True))
    ]


def ensure_editable(state: CircuitState, *, force: bool = False) -> None:
    """Structural edits rebuild the slots, so they are refused once it matters.

    `force` is kept from b2b: supervisors use it when a session has gone wrong
    mid-circuit and the alternative is abandoning it.
    """
    if force:
        return
    if state.active_slot_id is not None:
        raise CircuitLocked("A station is in progress; rebuilding the slots would delete it.")
    if state.has_feedback:
        raise CircuitLocked("Feedback has been recorded against these slots.")


def edit_block(state: CircuitState) -> str | None:
    """Why this circuit cannot be structurally edited, or None if it can.

    The same rule as `ensure_editable`, asked rather than asserted: the console
    needs to know before it offers an edit, instead of discovering the refusal
    after somebody has typed one. A stable code, not a sentence — b2b's client
    decides this by matching English.
    """
    if state.ended:
        return "circuit_ended"
    if state.active_slot_id is not None:
        return "consultation_in_progress"
    if state.has_feedback:
        return "feedback_recorded"
    return None


def ensure_startable(state: CircuitState) -> None:
    if state.ended:
        raise CircuitAlreadyEnded("That circuit has already finished.")


def ensure_live(state: CircuitState) -> None:
    """Nothing may act on a circuit that is over.

    Separate from `ensure_startable` because it guards a different moment: not
    "may this begin" but "is this still running". A switch that lands on an
    ended circuit leaves it showing a candidate consulting in a room that has
    already been torn down, and the trainee portal then offers a slot nobody
    can join.
    """
    if state.ended:
        raise CircuitAlreadyEnded("That circuit has already finished.")


def ensure_can_switch_turn(mode: Mode) -> None:
    if mode is not Mode.TRAINING:
        raise NotPermittedInMode(
            "Only a training circuit has a turn to switch; in an exam each candidate runs their own."
        )


def ensure_can_append_trainees(mode: Mode) -> None:
    if mode is not Mode.TRAINING:
        raise NotPermittedInMode("Candidates cannot be added to an exam circuit once it exists.")


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    low, high = bounds
    return max(low, min(high, value))


def normalise_timing(raw: Mapping[str, Any], *, mode: Mode = Mode.TRAINING, station_count: int = 0) -> Timing:
    """Read a timing blob, clamping it into what a station can actually run.

    The legacy `station_minutes` spelling is still accepted because existing
    circuits carry it. Clamping happens here rather than in the browser, which
    is where b2b does it today — so the API currently accepts any number at all.
    """
    # `is None` rather than `or`: a supplied zero means "clamp me to the
    # minimum", and treating it as missing would quietly hand back the default
    # instead — a three-minute reading period where one was asked for.
    reading_raw = raw.get("reading_minutes")
    reading = _clamp(int(DEFAULT_READING_MINUTES if reading_raw is None else reading_raw), READING_BOUNDS)

    simulation_raw = raw.get("simulation_minutes")
    if simulation_raw is None:
        simulation_raw = raw.get("station_minutes")
    simulation = _clamp(
        int(DEFAULT_SIMULATION_MINUTES if simulation_raw is None else simulation_raw),
        SIMULATION_BOUNDS,
    )

    breaks: tuple[Break, ...] = ()
    if mode is Mode.EXAM:
        # A break sits between stations, so it can only fall inside the circuit.
        highest = max(station_count - 1, 0)
        seen: set[int] = set()
        for entry in raw.get("breaks") or []:
            raw_after = entry.get("after_station")
            after = _clamp(int(0 if raw_after is None else raw_after), (1, highest)) if highest else 0
            if after and after not in seen:
                seen.add(after)
        breaks = tuple(Break(after) for after in sorted(seen))

    return Timing(reading_minutes=reading, simulation_minutes=simulation, breaks=breaks)
