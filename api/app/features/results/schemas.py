from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DecisionRead(BaseModel):
    revision: int
    workflow_state: str
    assessment_outcome: str | None
    recruitment_outcome: str | None
    rationale: str | None
    signed_off_at: datetime | None
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
    evidence: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int = Field(default=0, ge=0)


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


class ResultAcknowledgement(BaseModel):
    """A candidate's confirmation that they have read their result."""

    sitting_id: uuid.UUID
    acknowledged_at: datetime
