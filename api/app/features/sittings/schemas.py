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
