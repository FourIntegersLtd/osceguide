from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TraineeRead(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    cohort_id: uuid.UUID | None
    user_id: uuid.UUID | None
    access_revoked: bool


class CreateTrainee(BaseModel):
    email: EmailStr
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    cohort_id: uuid.UUID | None = None


MAX_BULK_TRAINEES = 500


class BulkCreateTrainees(BaseModel):
    """A spreadsheet's worth of trainees in one request.

    The browser parses the file; the API takes rows. Capped so one request
    cannot invite a whole university at once by accident.
    """

    trainees: list[CreateTrainee] = Field(min_length=1, max_length=MAX_BULK_TRAINEES)


class SkippedTrainee(BaseModel):
    email: str
    # A stable code the client switches on: `trainee_exists` for a duplicate
    # on the roster or within the upload.
    code: str


class BulkTraineesResult(BaseModel):
    """Who was added and who was not, so a partial upload is not a mystery."""

    created: list[TraineeRead] = Field(default_factory=list)
    skipped: list[SkippedTrainee] = Field(default_factory=list)


class CohortRead(BaseModel):
    id: uuid.UUID
    name: str
    academic_year: str | None
    status: str


class CreateCohort(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    academic_year: str | None = Field(default=None, max_length=32)


class GroupRead(BaseModel):
    id: uuid.UUID
    label: str
    member_count: int


class CreateGroup(BaseModel):
    label: str = Field(min_length=1, max_length=200)


class SetGroupMembers(BaseModel):
    trainee_ids: list[uuid.UUID]


class ResolveRosterRequest(BaseModel):
    """Who a circuit would name, before it is built."""

    trainee_ids: list[uuid.UUID] = Field(default_factory=list)
    group_ids: list[uuid.UUID] = Field(default_factory=list)


class RosterWarningRead(BaseModel):
    code: str
    group_id: uuid.UUID


class ResolvedRoster(BaseModel):
    """Who a circuit would actually contain, and what is missing.

    Returned before a circuit is built so a supervisor sees an empty linked
    group now rather than when the examination starts.
    """

    trainee_ids: list[uuid.UUID]
    warnings: list[RosterWarningRead] = Field(default_factory=list)


class TraineeAccess(BaseModel):
    revoked: bool
    at: datetime | None = None
