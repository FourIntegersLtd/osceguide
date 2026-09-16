from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SlotRead(BaseModel):
    id: uuid.UUID
    slot_index: int
    trainee_id: uuid.UUID
    station_version_id: uuid.UUID
    status: str
    room_name: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class TimingRead(BaseModel):
    reading_minutes: int
    simulation_minutes: int
    breaks: list[int] = Field(default_factory=list)


class CircuitRead(BaseModel):
    id: uuid.UUID
    sitting_id: uuid.UUID
    name: str
    supervisor_user_id: uuid.UUID | None
    timing: TimingRead
    active_slot_id: uuid.UUID | None
    room_name: str | None
    started_at: datetime | None
    ended_at: datetime | None
    slots: list[SlotRead] = Field(default_factory=list)


class SittingRead(BaseModel):
    id: uuid.UUID
    name: str
    mode: str
    sitting_type: str
    status: str
    scheduled_for: datetime | None
    feedback_template_version_id: uuid.UUID
    circuits: list[CircuitRead] = Field(default_factory=list)


class CreateSitting(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    feedback_template_version_id: uuid.UUID
    mode: str = Field(default="training", pattern="^(training|exam)$")
    sitting_type: str = Field(default="group_training", max_length=32)
    scheduled_for: datetime | None = None
    programme_id: uuid.UUID | None = None


class TimingIn(BaseModel):
    reading_minutes: int | None = None
    simulation_minutes: int | None = None
    breaks: list[int] = Field(default_factory=list)


class CreateCircuit(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trainee_ids: list[uuid.UUID]
    station_version_ids: list[uuid.UUID]
    supervisor_user_id: uuid.UUID | None = None
    timing: TimingIn = Field(default_factory=TimingIn)


class SwitchTurn(BaseModel):
    slot_id: uuid.UUID


class AppendTrainee(BaseModel):
    trainee_id: uuid.UUID
    station_version_id: uuid.UUID


class DispatchAgent(BaseModel):
    """Which slot the agent is being dispatched for.

    Named rather than taken from `active_slot_id`, so dispatching and switching
    are separate decisions: a supervisor can re-dispatch the current station
    without the circuit's state having to be right first.
    """

    slot_id: uuid.UUID


class DispatchResult(BaseModel):
    room_name: str
    slot_id: uuid.UUID
    # The attempt the worker will bootstrap. A re-dispatch is a new attempt,
    # so this changes each time (C6).
    attempt_id: uuid.UUID
    agent_name: str
    stale_agents_removed: int


class ConsultationEnded(BaseModel):
    circuit_id: uuid.UUID
    agents_removed: int
    # Null while the circuit is still running: ending a consultation is not
    # ending the circuit.
    ended_at: datetime | None


class EditLock(BaseModel):
    circuit_id: uuid.UUID
    editable: bool
    # A stable code the client switches on, never a sentence.
    reason: str | None


class AppendTrainees(BaseModel):
    trainee_ids: list[uuid.UUID] = Field(min_length=1)
