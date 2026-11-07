"""The shapes another slice may ask about sittings in, as plain dataclasses.

The projections themselves live in `dashboard`; this is the part only this
slice can answer, so the tenant scoping keeps one home rather than two. Filled
by `service_reads.py`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.features.sittings.schemas import TimingRead


@dataclass(frozen=True)
class SittingRef:
    """A sitting as a line on somebody else's screen."""

    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    mode: str
    sitting_type: str
    status: str
    scheduled_for: datetime | None
    rubric_version_id: uuid.UUID
    programme_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CircuitRef:
    """A circuit as another slice's screen would show it."""

    id: uuid.UUID
    sitting_id: uuid.UUID
    name: str
    supervisor_user_id: uuid.UUID | None
    # Already resolved to the defaults a circuit runs with, so a caller does
    # not re-implement the clamping this slice owns.
    timing: TimingRead
    active_slot_id: uuid.UUID | None
    room_name: str | None
    agent_dispatched_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    # The examination clock, which is the circuit's (D-6).
    phase: str | None = None
    phase_started_at: datetime | None = None
    phase_ends_at: datetime | None = None
    phase_seq: int = 0
    paused_at: datetime | None = None
    paused_seconds: int = 0
    auto_advance: bool = True
    voice_fault_at: datetime | None = None
    # Set when the supervisor closes a training room that was kept open after End.
    room_closed_at: datetime | None = None
    # Whether the supervisor opened the floor to every microphone (training rooms).
    open_floor: bool = False
    # Raised by each edit; an edit made from an older read is refused (B-15).
    revision: int = 1


@dataclass(frozen=True)
class SlotRef:
    """A slot as another slice's screen would show it."""

    id: uuid.UUID
    circuit_id: uuid.UUID
    slot_index: int
    trainee_id: uuid.UUID
    station_version_id: uuid.UUID
    status: str
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    exam_completed_at: datetime | None


@dataclass(frozen=True)
class SupervisorCircuit:
    """One row of "circuits assigned to me"."""

    circuit: CircuitRef
    sitting: SittingRef
    slot_count: int


@dataclass(frozen=True)
class CircuitDetail:
    """Everything one console screen needs from this slice."""

    circuit: CircuitRef
    sitting: SittingRef
    slots: list[SlotRef] = field(default_factory=list)


@dataclass(frozen=True)
class TraineeSlot:
    """A slot a trainee is rostered onto, with the sitting it belongs to."""

    slot: SlotRef
    circuit: CircuitRef
    sitting: SittingRef


@dataclass(frozen=True)
class SittingDetail:
    """A sitting with every circuit and slot, for a report over all of it."""

    sitting: SittingRef
    circuits: list[CircuitDetail] = field(default_factory=list)


@dataclass(frozen=True)
class CircuitRun:
    """One finished run of a circuit, as it stood when it ended."""

    id: uuid.UUID
    circuit_id: uuid.UUID | None
    circuit_name: str
    sitting_id: uuid.UUID | None
    sitting_name: str
    mode: str
    supervisor_user_id: uuid.UUID | None
    started_at: datetime | None
    ended_at: datetime
    candidate_count: int
    stations_total: int
    stations_completed: int
    status: str
