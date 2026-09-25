"""The cohort read-out: the document an institution downloads after an examination.

A thin projection: the ranked candidates are the same `CohortCandidate` rows
`/sittings/{id}/cohort` already serves. What is added here is the part a screen cannot be
trusted to derive — the totals, the priorities counted, the recommendation sentences and
the statement of how the numbers were arrived at — so that two institutions printing the
same sitting get the same page.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.features.dashboard.schemas_org import CohortCandidate

# Bumped when the shape or the arithmetic of a read-out changes, so a document
# kept for six months still says which rules produced it.
# Oracle: b2b's `READOUT_VERSION`.
READOUT_VERSION = "1"


class ReadoutSitting(BaseModel):
    """The sitting, as the head of the document states it."""

    sitting_id: str
    name: str
    scheduled_for: datetime | None = None
    # How many stations a candidate on this sitting was expected to sit. The
    # legacy read-out called it `requiredStationCount`, and it is the denominator
    # every completion figure below is a fraction of.
    required_station_count: int


class ReadoutSummary(BaseModel):
    """What the cohort adds up to. Counts, not judgements."""

    cohort_size: int
    fully_complete_count: int
    # None when nobody has been marked yet — which is not the same document as
    # one that says the cohort averaged zero.
    average_assessment_score: float | None
    priorities: dict[str, int] = Field(default_factory=dict)
    computed_at: datetime


class SittingReadout(BaseModel):
    """Everything the read-out says, in the order it says it."""

    readout_version: str = READOUT_VERSION
    generated_at: datetime
    org_slug: str
    sitting: ReadoutSitting
    summary: ReadoutSummary
    # Sentences, not a schema: they are what a course lead reads, and turning
    # them into fields would only move the reading into the browser.
    recommendations: list[str] = Field(default_factory=list)
    candidates: list[CohortCandidate] = Field(default_factory=list)
    # The arithmetic in the document's own words, so a number cannot be argued
    # with months later by somebody who never saw how it was made.
    methodology: str
