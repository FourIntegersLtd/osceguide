"""What the roster's routes read and return: trainees, their cohorts and
groups, and the result of adding a spreadsheet's worth of people at once.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.pagination import Page
from app.core.schemas import InvitationRead as InvitationRead


class TraineeRead(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    cohort_id: uuid.UUID | None
    user_id: uuid.UUID | None
    access_revoked: bool
    anonymised: bool = False
    # Filled by the list read: true while the person's account was made by an
    # invitation and nobody has used it, so "Resend invitation" has something
    # to resend.
    invitation_pending: bool = False
    # Filled by the list read: the programmes of the sittings this trainee is
    # rostered on (exam names, sorted) and how many stations they have sat.
    programme_names: list[str] = Field(default_factory=list)
    stations_sat: int = 0
    # Filled by the list read: whether the linked account holds a live membership here.
    is_member: bool = False
    # True when adding created the account with the temporary password the admin typed.
    temporary_password_applied: bool = False


class TraineePage(Page[TraineeRead]):
    """A roster page that also says how many people match, so the first load need not walk it all."""

    total_count: int


class CreateTrainee(BaseModel):
    email: EmailStr
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    cohort_id: uuid.UUID | None = None
    # For when the invitation email cannot be delivered: a brand-new account gets this
    # password (changed at first sign-in) instead of an email. Ignored for an existing account.
    temporary_password: str | None = Field(default=None, min_length=1, max_length=512)


class UpdateTrainee(BaseModel):
    """Correct a trainee's name or intake. Fields left out are unchanged; a field sent
    as null clears it. The email address cannot be changed here. Group membership is
    set separately via `PUT /trainee-groups/{id}/members`.
    """

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    cohort_id: uuid.UUID | None = None


# The browser sends rows in chunks of IMPORT_CHUNK (web roster api.ts); keep the two equal.
MAX_BULK_TRAINEES = 500


class BulkCreateTrainees(BaseModel):
    """A spreadsheet's worth of trainees in one request.

    The browser parses the file and sends it in chunks of `MAX_BULK_TRAINEES`.
    More than that in one request is refused `too_many_trainees` by the service,
    whose message names the limit (a schema `max_length` answered a bare
    "The request was not valid").
    """

    trainees: list[CreateTrainee] = Field(min_length=1)


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
    # Sittings held for this intake: deleting it detaches them (the column is SET NULL).
    sitting_count: int = 0


class CreateCohort(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    academic_year: str | None = Field(default=None, max_length=32)


class UpdateCohort(BaseModel):
    """Rename an intake, or say which academic year it belongs to. Fields left out
    are unchanged.
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
    """Rename a group. Membership does not change."""

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


class BulkTraineeIds(BaseModel):
    """A batch of roster ids, for a bulk action from a selection in the roster
    table. Capped the same as a bulk upload, so a selected page cannot name a
    whole institution's roster by accident.
    """

    trainee_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_BULK_TRAINEES)


class BulkTraineeAccessResult(BaseModel):
    """One row's outcome from a bulk revoke: whether this call changed anything,
    or the row was already in that state or not this organisation's to change.
    """

    trainee_id: uuid.UUID
    outcome: str  # "revoked" | "already_revoked" | "not_found"


class BulkTraineeAccessResponse(BaseModel):
    results: list[BulkTraineeAccessResult]


class BulkSetTraineeCohort(BaseModel):
    """Move a batch of trainees into one intake at once, or out of any intake."""

    trainee_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_BULK_TRAINEES)
    cohort_id: uuid.UUID | None = None


class BulkTraineeCohortResult(BaseModel):
    trainee_id: uuid.UUID
    outcome: str  # "updated" | "not_found"


class BulkTraineeCohortResponse(BaseModel):
    results: list[BulkTraineeCohortResult]


class BulkTraineeInvitationResult(BaseModel):
    trainee_id: uuid.UUID
    outcome: str  # "sent" | "already_signed_in" | "not_found"


class BulkTraineeInvitationResponse(BaseModel):
    results: list[BulkTraineeInvitationResult]
