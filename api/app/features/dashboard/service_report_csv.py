"""The sitting report as a spreadsheet an administrator can open in Excel.

Built from the same report the results screen reads, so the file cannot
disagree with that screen. A second query path would drift the moment one
of them changed.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.dashboard.schemas_report import CandidateReport, DecisionSummary, SittingReport
from app.features.dashboard.service_report import build_sitting_report
from app.features.tenancy import service_audit as audit

# Characters Excel treats as the start of a formula. A name that begins with
# one of them would otherwise run when the file is opened.
SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def spreadsheet_cell(value: str) -> str:
    """Text safe to open in a spreadsheet.

    A cell whose text starts with a formula character is prefixed with a
    quote, so Excel shows the characters rather than evaluating them.
    """
    if value.startswith(SPREADSHEET_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def results_csv_columns() -> list[str]:
    """The header row: identity, how many stations, the reviewers' ratings, then every decision field."""
    decision_columns = [f"decision_{field_name}" for field_name in DecisionSummary.model_fields]
    return [
        "name",
        "email",
        "user_id",
        "trainee_id",
        "stations",
        "stations_marked",
        "overall_rag",
        "score",
        "stations_passed",
        *decision_columns,
    ]


def render_sitting_results_csv(report: SittingReport) -> bytes:
    """UTF-8 CSV of one report, with a BOM so Excel reads accented names.

    `stations` is how many stations the candidate sat. The station list itself
    is nested, and a spreadsheet row is one flat line beside `stations_marked`.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(results_csv_columns())
    for candidate in report.candidates:
        writer.writerow(_candidate_row(candidate))
    return buffer.getvalue().encode("utf-8-sig")


async def export_sitting_results(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    sitting_id: uuid.UUID,
    actor: Principal,
) -> tuple[bytes, str]:
    """The sitting report as a CSV file, and an audit row for the download."""
    report = await build_sitting_report(session, org_id, sitting_id)
    payload = render_sitting_results_csv(report)
    filename = f"{_filename_stem(report.sitting.name, report.sitting.id)}-results.csv"
    await audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="results.exported",
        target_type="sitting",
        target_id=str(sitting_id),
        summary=f"Downloaded results for sitting {sitting_id} as CSV",
    )
    return payload, filename


def _filename_stem(sitting_name: str, sitting_id: uuid.UUID) -> str:
    """A file-name stem: the sitting's name as a slug, or its id."""
    slug = re.sub(r"[^a-z0-9]+", "-", sitting_name.casefold()).strip("-")
    return slug or str(sitting_id)


def _candidate_row(candidate: CandidateReport) -> list[str]:
    """One candidate as spreadsheet cells, decision fields flattened."""
    return [
        spreadsheet_cell(candidate.name or ""),
        spreadsheet_cell(candidate.email or ""),
        spreadsheet_cell(str(candidate.user_id)),
        spreadsheet_cell("" if candidate.trainee_id is None else str(candidate.trainee_id)),
        spreadsheet_cell(str(len(candidate.stations))),
        spreadsheet_cell(str(candidate.stations_marked)),
        spreadsheet_cell(_cell_value(candidate.overall_rag)),
        spreadsheet_cell(_cell_value(candidate.score)),
        spreadsheet_cell(str(candidate.stations_passed)),
        *_decision_cells(candidate.decision),
    ]


def _cell_value(value: object) -> str:
    """A native rating or a score as a cell: "G", "7", "yes"/"no", "66.5", or empty for none."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _decision_cells(decision: DecisionSummary | None) -> list[str]:
    """Every decision field, prefixed in the header and empty when there is none."""
    cells: list[str] = []
    for field_name in DecisionSummary.model_fields:
        if decision is None:
            cells.append("")
            continue
        value = getattr(decision, field_name)
        if isinstance(value, datetime):
            cells.append(spreadsheet_cell(value.isoformat()))
        elif value is None:
            cells.append("")
        else:
            cells.append(spreadsheet_cell(str(value)))
    return cells
