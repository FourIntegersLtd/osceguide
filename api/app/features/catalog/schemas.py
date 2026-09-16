from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ExamRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    framework_id: str
    default_reading_seconds: int
    default_simulation_seconds: int
    station_attempt_limit: int


class ProgrammeRead(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    exam_code: str
    exam_name: str
    status: str
    source: str


class CreateProgramme(BaseModel):
    exam_code: str = Field(min_length=1, max_length=32)


class UpdateProgramme(BaseModel):
    status: str = Field(pattern="^(draft|active|retired)$")
