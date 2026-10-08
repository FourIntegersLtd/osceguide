"""Reporting across sittings: one row per programme, from data the sittings already hold."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ProgrammeReportRow(BaseModel):
    programme_id: uuid.UUID
    exam_name: str
    sittings: int
    # Distinct people rostered onto the programme's circuits.
    candidates: int
    # Decisions released to candidates, and how many of those were a pass.
    released: int
    passed: int
    # Percent of released decisions that passed; null while none is released.
    pass_rate: float | None


class OrgReporting(BaseModel):
    programmes: list[ProgrammeReportRow]
