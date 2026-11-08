"""What the results routes accept and return: a candidate's decision and their own view of it."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DecisionRead(BaseModel):
    revision: int
    workflow_state: str
    assessment_outcome: str | None
    recruitment_outcome: str | None
    rationale: str | None
    signed_off_at: datetime | None
    # Display name of whoever signed it off (their email if they have no name); null before sign-off.
    signed_off_by_name: str | None = None
    released_at: datetime | None


class SaveDecision(BaseModel):
    """A decision to save as a draft.

    `expected_revision` is the revision this screen last read, or 0 when it has
    read nothing. A save that does not name the current one is refused with
    `decision_revised` (409), so two administrators cannot overwrite each
    other's draft.
    """

    assessment_outcome: str | None = Field(default=None, pattern="^(pass|fail|inconclusive|withheld)$")
    recruitment_outcome: str | None = Field(
        default=None, pattern="^(hired|reserve|not_hired|withdrawn|pending)$"
    )
    rationale: str | None = Field(default=None, max_length=4000)
    moderation_notes: str | None = None
    expected_revision: int = Field(default=0, ge=0)


MAX_BULK_RELEASE = 500


# One candidate in a bulk release. The server reads the evidence from the marking itself (R-25).
class BulkReleaseCandidate(BaseModel):
    trainee_id: uuid.UUID


class BulkRelease(BaseModel):
    """Several signed-off candidates to release at once.

    Each carries its own evidence: a release re-checks it against what was
    signed off, candidate by candidate.
    """

    candidates: list[BulkReleaseCandidate] = Field(min_length=1, max_length=MAX_BULK_RELEASE)


class ReleasedCandidate(BaseModel):
    trainee_id: uuid.UUID
    decision: DecisionRead


class SkippedRelease(BaseModel):
    trainee_id: uuid.UUID
    # The refusal the single release route would have returned, e.g.
    # `invalid_workflow` or `evidence_changed`.
    code: str


class BulkReleaseResult(BaseModel):
    """Who was released and who was not, so a partial release is not a mystery."""

    released: list[ReleasedCandidate] = Field(default_factory=list)
    skipped: list[SkippedRelease] = Field(default_factory=list)


class SignedOffCandidate(BaseModel):
    trainee_id: uuid.UUID
    decision: DecisionRead


class BulkSignOffResult(BaseModel):
    """Who the sheet-level sign-off signed, in roster order."""

    signed_off: list[SignedOffCandidate] = Field(default_factory=list)


class TraineeStationResult(BaseModel):
    """One station of a released result, as its candidate reads it (T-8)."""

    slot_id: uuid.UUID
    station_title: str | None
    # 0-100, or null while nothing of this station is rated.
    score: float | None
    # By the rubric's pass rule; null when it sets none.
    passed: bool | None


class TraineeResultRead(BaseModel):
    """A candidate's own view of their result.

    Deliberately narrower than the internal record: moderation notes and the
    evidence snapshot stay internal.
    """

    sitting_id: uuid.UUID
    assessment_outcome: str | None
    rationale: str | None
    released_at: datetime | None
    # The same 0–100 mean the staff ranking already computes from marked
    # stations. Null when nothing has been marked. A pass threshold is not
    # stored on the decision, so it is not sent — inventing 60 here would
    # publish a bar the examiner never set.
    assessment_score: float | None = None
    # When this candidate confirmed they had read it. Null until they do; a new
    # revision is a new decision and needs its own acknowledgement.
    acknowledged_at: datetime | None = None
    # Each station the candidate sat, in running order (T-8).
    stations: list[TraineeStationResult] = Field(default_factory=list)


class ResultAcknowledgement(BaseModel):
    """A candidate's confirmation that they have read their result."""

    sitting_id: uuid.UUID
    acknowledged_at: datetime
