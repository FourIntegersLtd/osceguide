"""How a sitting is built and run.

A **sitting** is a scheduled event an organisation holds. It contains
**circuits**, and a circuit contains **slots** — one trainee at one station.

- `training`: several trainees rotate through several stations together, one
  active at a time, driven by a supervisor.
- `exam`: one candidate works through every station of their own circuit,
  starting each themselves.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# Oracle: `EXAM_MAX_STATIONS` in b2b's slot_builder.
EXAM_MAX_STATIONS = 12

DEFAULT_READING_MINUTES = 3
DEFAULT_SIMULATION_MINUTES = 10
DEFAULT_BREAK_MINUTES = 5
READING_BOUNDS = (1, 30)
SIMULATION_BOUNDS = (1, 180)
BREAK_BOUNDS = (1, 60)


class Mode(StrEnum):
    """Which shape of circuit this is: a group rotating together, or one candidate alone."""

    TRAINING = "training"
    EXAM = "exam"


class SlotStatus(StrEnum):
    """Where one trainee's station has got to.

    `SKIPPED` is a station the circuit moved past: jumped over, or left unsat
    when the examination was ended early. Not `COMPLETED` (nothing was
    recorded) and not `SCHEDULED` (it is not coming).
    """

    SCHEDULED = "scheduled"
    READING = "reading"
    IN_CONSULTATION = "in_consultation"
    COMPLETED = "completed"
    SKIPPED = "skipped"


# A station that will not be sat again, whichever way it ended.
FINISHED_SLOT_STATUSES = frozenset({SlotStatus.COMPLETED, SlotStatus.SKIPPED})


class InvalidCircuit(Exception):
    """A circuit was asked to be built, or its timing set, in a way the rules refuse."""


class CircuitLocked(Exception):
    """A structural edit was refused because the circuit's slots already mean something."""


class CircuitAlreadyEnded(Exception):
    """An action needs a circuit that is still open, and this one has finished."""


class NotPermittedInMode(Exception):
    """An action was tried against the wrong kind of circuit (training or exam)."""


@dataclass(frozen=True)
class PlannedSlot:
    """One slot a circuit will start with, before it is written to the database."""

    index: int
    # A `users.id`, not a `trainees.id` — see the trainee_id trap in AGENTS.md.
    trainee_user_id: str
    station_version_id: str


@dataclass(frozen=True)
class CircuitState:
    """The facts about a circuit that the edit and start rules need, gathered in one place."""

    active_slot_id: str | None
    has_feedback: bool
    ended: bool = False


@dataclass(frozen=True)
class Break:
    """One scheduled rest, named by the station it follows (1-based, as an examiner writes it)."""

    after_station: int


@dataclass(frozen=True)
class Timing:
    """How long each phase lasts, and where the breaks fall, once defaults and limits are applied."""

    reading_minutes: int
    simulation_minutes: int
    # A break used to be a position with no duration, so nothing could count
    # one down and the circuit had no way to know when it was over.
    break_minutes: int = DEFAULT_BREAK_MINUTES
    breaks: tuple[Break, ...] = ()


def build_slots(
    mode: Mode, *, trainee_user_ids: Sequence[str], station_version_ids: Sequence[str]
) -> list[PlannedSlot]:
    """The slots a circuit starts with: an exam candidate sits every station,
    a training group rotates so each trainee starts at a different one."""
    if not station_version_ids:
        raise InvalidCircuit("A circuit needs at least one station.")

    if mode is Mode.EXAM:
        if len(trainee_user_ids) != 1:
            raise InvalidCircuit("An exam circuit is one candidate's sitting.")
        if len(station_version_ids) > EXAM_MAX_STATIONS:
            raise InvalidCircuit(f"An exam circuit takes at most {EXAM_MAX_STATIONS} stations.")
        return [
            PlannedSlot(index, trainee_user_ids[0], station_version_id)
            for index, station_version_id in enumerate(station_version_ids)
        ]

    if len(trainee_user_ids) != len(station_version_ids):
        raise InvalidCircuit(
            "A training circuit needs one station per trainee, so everyone starts somewhere."
        )
    return [
        PlannedSlot(index, trainee_user_id, station_version_id)
        for index, (trainee_user_id, station_version_id) in enumerate(
            zip(trainee_user_ids, station_version_ids, strict=True)
        )
    ]


def ensure_editable(state: CircuitState, *, force: bool = False) -> None:
    """Structural edits rebuild the slots, so they are refused once it matters.

    `force` overrides this when a session has gone wrong mid-circuit and the
    alternative is abandoning it.
    """
    if force:
        return
    if state.active_slot_id is not None:
        raise CircuitLocked("A station is in progress; rebuilding the slots would delete it.")
    if state.has_feedback:
        raise CircuitLocked("Feedback has been recorded against these slots.")


def edit_block(state: CircuitState) -> str | None:
    """Why this circuit cannot be structurally edited, or None if it can.

    Same rule as `ensure_editable`, checked ahead of time so the console can
    decide whether to offer an edit before a supervisor tries one. Returns a
    stable code, not a sentence.
    """
    if state.ended:
        return "circuit_ended"
    if state.active_slot_id is not None:
        return "consultation_in_progress"
    if state.has_feedback:
        return "feedback_recorded"
    return None


def ensure_startable(state: CircuitState) -> None:
    """Refuse to start a circuit that has already finished."""
    if state.ended:
        raise CircuitAlreadyEnded("That circuit has already finished.")


def ensure_live(state: CircuitState) -> None:
    """Nothing may act on a circuit that is over.

    Separate from `ensure_startable`: guards "is this still running", not "may
    this begin". Without it, an ended circuit can keep showing a candidate
    consulting in a room that no longer exists.
    """
    if state.ended:
        raise CircuitAlreadyEnded("That circuit has already finished.")


def ensure_can_append_trainees(mode: Mode) -> None:
    """Latecomers belong to a training circuit, and to nobody else.

    An exam circuit is one candidate through every station, so a second person
    on it is not a late arrival but a second candidate sharing one room, clock
    and recording — and a transcript that would be marked as though one doctor
    produced it. A new exam candidate gets their own circuit on the sitting
    instead (`POST /sittings/{id}/circuits`).
    """
    if mode is not Mode.TRAINING:
        raise NotPermittedInMode(
            "Candidates cannot be added to an exam circuit. Give them their own circuit on this sitting."
        )


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    """Restrict `value` to sit within `bounds` (inclusive)."""
    low, high = bounds
    return max(low, min(high, value))


def normalise_timing(raw: Mapping[str, Any], *, mode: Mode = Mode.TRAINING, station_count: int = 0) -> Timing:
    """Read a timing blob, clamping it into what a station can actually run.

    The legacy `station_minutes` spelling is still accepted because existing
    circuits carry it.
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

    break_raw = raw.get("break_minutes")
    break_minutes = _clamp(int(DEFAULT_BREAK_MINUTES if break_raw is None else break_raw), BREAK_BOUNDS)

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

    return Timing(
        reading_minutes=reading,
        simulation_minutes=simulation,
        break_minutes=break_minutes,
        breaks=breaks,
    )
