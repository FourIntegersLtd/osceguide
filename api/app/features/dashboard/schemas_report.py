"""The sitting report: what a course lead reads back after an examination.

One request for the whole sitting, per candidate: which stations they sat,
whether each was marked, what the reviewers agreed, and where the formal
decision stands. The legacy backend had a cohort summary and candidate packs;
this platform had the per-slot review list and nothing over a sitting.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.features.dashboard.schemas_org import ConsoleSitting


class StationReport(BaseModel):
    slot_id: uuid.UUID
    circuit_id: uuid.UUID
    circuit_name: str
    slot_index: int
    station_title: str | None
    slot_status: str
    # The live attempt's status, or null if the station was never dispatched.
    attempt_status: str | None
    # Marked by the engine: the attempt reached `evaluated`.
    marked: bool
    # What the completed human reviews agreed, worst wins per domain.
    overall_rag: str | None
    by_domain: dict[str, str] = Field(default_factory=dict)


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
    overall_rag: str | None
    # Null until an institution admin has saved a decision.
    decision: DecisionSummary | None


class ReportTotals(BaseModel):
    candidates: int
    stations: int
    stations_marked: int
    decisions_released: int


class SittingReport(BaseModel):
    sitting: ConsoleSitting
    totals: ReportTotals
    candidates: list[CandidateReport] = Field(default_factory=list)
