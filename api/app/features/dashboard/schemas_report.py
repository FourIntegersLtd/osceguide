"""The sitting report: what a course lead reads back after an examination.

One request for the whole sitting, per candidate: which stations they sat, whether each
was marked, what the reviewers agreed, and where the formal decision stands.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.schemas import RatingRead, RatingValueRead
from app.features.dashboard.schemas_org import ConsoleSitting


class StationReport(BaseModel):
    slot_id: uuid.UUID
    circuit_id: uuid.UUID
    circuit_name: str
    slot_index: int
    station_title: str | None
    slot_status: str
    # The live attempt's id, or null if the station was never dispatched. A
    # reviewer opening a slot needs it to read the engine's marking beside their
    # own, and `/slots/{id}/reviews` does not carry one.
    attempt_id: uuid.UUID | None
    # The live attempt's status, or null if the station was never dispatched.
    attempt_status: str | None
    # Marked: the engine evaluated the attempt, or a human review was completed.
    marked: bool
    # A skipped station nobody marked: a deliberate absent result, left out of
    # the "all marked" count rather than counted as unmarked (R-42).
    absent: bool = False
    # What the completed human reviews agreed, in the rubric's own rating: per
    # domain the reviewers combined, overall the worst domain. The name keeps
    # `rag` until the web app reads the rubric's own rating fields.
    overall_rag: RatingValueRead | None
    by_domain: dict[str, RatingValueRead] = Field(default_factory=dict)
    # 0-100 after any GP-lead review (the cohort ranking's number), and whether it passes.
    score: float | None = None
    passed: bool | None = None


class DecisionSummary(BaseModel):
    workflow_state: str
    assessment_outcome: str | None
    recruitment_outcome: str | None
    signed_off_at: datetime | None
    released_at: datetime | None


class CandidateReport(BaseModel):
    user_id: uuid.UUID
    # Null when the candidate is not on the roster: a slot names a user.
    trainee_id: uuid.UUID | None
    name: str | None
    email: str | None
    stations: list[StationReport] = Field(default_factory=list)
    stations_marked: int
    # Worst wins across the candidate's stations, the same rule as within one.
    overall_rag: RatingValueRead | None
    # The mean station score (0-100), and how many stations passed.
    score: float | None = None
    stations_passed: int = 0
    # Null until an institution admin has saved a decision.
    decision: DecisionSummary | None


class ReportTotals(BaseModel):
    candidates: int
    stations: int
    stations_marked: int
    decisions_released: int
    # Candidates who sat at least one station that the engine has not marked yet.
    awaiting_marking: int = 0


class SittingReport(BaseModel):
    sitting: ConsoleSitting
    # How the ratings in this report read: the sitting's rubric's rating.
    rating: RatingRead | None = None
    totals: ReportTotals
    candidates: list[CandidateReport] = Field(default_factory=list)
