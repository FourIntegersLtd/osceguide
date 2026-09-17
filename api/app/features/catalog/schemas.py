from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ExamRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    status: str
    rubric_version_id: uuid.UUID | None = None
    # The rubric version's id: what a result is recorded under. Empty while the
    # exam is a draft with no rubric named yet.
    framework_id: str
    default_reading_seconds: int
    default_simulation_seconds: int
    station_attempt_limit: int
    partner_pilot: bool = False


class CreateExam(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    default_reading_seconds: int = Field(gt=0, le=3600)
    default_simulation_seconds: int = Field(gt=0, le=7200)
    station_attempt_limit: int = Field(default=3, gt=0, le=100)
    rubric_version_id: uuid.UUID | None = None
    partner_pilot: bool = False


class UpdateExam(BaseModel):
    """Everything but the code, which existing plans and ref ids depend on."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    default_reading_seconds: int | None = Field(default=None, gt=0, le=3600)
    default_simulation_seconds: int | None = Field(default=None, gt=0, le=7200)
    station_attempt_limit: int | None = Field(default=None, gt=0, le=100)
    rubric_version_id: uuid.UUID | None = None
    partner_pilot: bool | None = None


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
