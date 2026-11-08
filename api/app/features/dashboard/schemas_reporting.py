"""Reporting across sittings: one row per programme, from data the sittings already hold."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ProgrammeReportRow(BaseModel):
    programme_id: uuid.UUID
    # The exam behind the programme, so a row can open it.
    exam_id: uuid.UUID
    exam_name: str
    sittings: int
    # Distinct people rostered onto the programme's circuits.
    candidates: int
    # Decisions released to candidates, and how many of those were a pass.
    released: int
    passed: int
    # Percent of released decisions that passed; null while none is released.
    pass_rate: float | None


class StationReportRow(BaseModel):
    """One station across every released result that sat it."""

    station_title: str
    # Released candidate-stations the station was rated for.
    assessed: int
    # Percent of those that passed by the rubric's rule; null when the rubric sets no pass rule.
    pass_rate: float | None
    # The rated domain with the lowest mean score across them; null when nothing is rated.
    weakest_competency: str | None


class OrgReporting(BaseModel):
    programmes: list[ProgrammeReportRow]
    # Weakest pass rate first, from released results only.
    stations: list[StationReportRow] = []
    # Different staff who have completed a review of a station, across all time.
    assessors_marking: int = 0
