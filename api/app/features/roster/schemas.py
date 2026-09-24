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
    anonymised: bool = False


class CreateTrainee(BaseModel):
    email: EmailStr
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    cohort_id: uuid.UUID | None = None


class UpdateTrainee(BaseModel):
    """The roster edit screen's fields. Absent means "leave it alone", sent means
    "write this", including a null that clears it.

    Not the address: `email` is what identifies the entry inside the
    organisation (unique per org, and the account link is made against it), so
    editing it is not correcting a typo but re-pointing a person's results. The
    b2b edit screen offered first name, last name and the group; the group is
    `cohort_id` here, and the other half of the legacy's `cohort` string — the
    list a circuit is built from — is a membership row rather than a field, so
    it is set by `PUT /trainee-groups/{id}/members`.
    """

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    cohort_id: uuid.UUID | None = None


class InvitationRead(BaseModel):
    """A re-sent invitation, answered with what the email actually says.

    The token itself is not here: it is a credential, and it goes only to the
    address it was minted for.
    """

    email: str
    invited_to: str


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


class UpdateCohort(BaseModel):
    """Rename an intake, or say which academic year it belongs to.

    Absent means "leave it alone". b2b's `examIds` is not here: which exams a
    cohort is bound to is `catalog`'s answer, and this slice's row carries no
    such column, so exposing the field would promise a write that goes nowhere.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    academic_year: str | None = Field(default=None, max_length=32)


class GroupRead(BaseModel):
    id: uuid.UUID
    label: str
    member_count: int


class CreateGroup(BaseModel):
    label: str = Field(min_length=1, max_length=200)


class UpdateGroup(BaseModel):
    """Rename a group. Who is in it does not move with the name — that is the
    whole of why membership is a table here and a matched string in b2b."""

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
