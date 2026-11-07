"""The shortlist: decided candidates, best first, as a spreadsheet an assessor lead can circulate.

Only a signed-off or released decision with a real outcome is listed (a draft is not a decision, and
a withheld one is deliberately not shared). Built from the sitting report and the decisions the
results slice holds, so it cannot disagree with the results screen. The reason is the decision's
rationale, which the report itself leaves out, so the route is org admin only.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.features.dashboard.schemas_report import CandidateReport
from app.features.dashboard.service_report import build_sitting_report
from app.features.dashboard.service_report_csv import filename_stem, spreadsheet_cell, stream_csv
from app.features.results import service as results
from app.features.results.schemas import DecisionRead
from app.features.tenancy import service_audit as audit

SHORTLIST_COLUMNS = ["rank", "name", "email", "score", "outcome", "reason"]
_DECIDED = ("signed_off", "released")


def _outcome(decision: DecisionRead) -> str:
    return decision.recruitment_outcome or decision.assessment_outcome or ""


def _is_decided(decision: DecisionRead | None) -> bool:
    """Signed off or released with a real outcome: a draft or a withheld one is not shared."""
    return (
        decision is not None
        and decision.workflow_state in _DECIDED
        and decision.assessment_outcome not in (None, "withheld")
    )


def ranked_shortlist(
    candidates: list[CandidateReport], decisions: dict[uuid.UUID, DecisionRead]
) -> list[tuple[int | None, CandidateReport, DecisionRead]]:
    """Decided candidates best first on the displayed (rounded) score, then stations passed.

    Level on both share a rank and the next skips (1, 1, 3), as the on-screen ranking does; nobody
    without a score is ranked and they come last.
    """
    decided = [
        (candidate, decisions[candidate.trainee_id])
        for candidate in candidates
        if candidate.trainee_id is not None and _is_decided(decisions.get(candidate.trainee_id))
    ]
    scored = sorted(
        (pair for pair in decided if pair[0].score is not None),
        key=lambda pair: (-round(pair[0].score or 0), -pair[0].stations_passed, pair[0].name or ""),
    )
    rows: list[tuple[int | None, CandidateReport, DecisionRead]] = []
    for at, (candidate, decision) in enumerate(scored):
        before = scored[at - 1][0] if at else None
        level = (
            before is not None
            and round(before.score or 0) == round(candidate.score or 0)
            and before.stations_passed == candidate.stations_passed
        )
        rank = rows[-1][0] if level else at + 1
        rows.append((rank, candidate, decision))
    rows.extend(
        (None, candidate, decision)
        for candidate, decision in sorted(decided, key=lambda pair: pair[0].name or "")
        if candidate.score is None
    )
    return rows


def _row(rank: int | None, candidate: CandidateReport, decision: DecisionRead) -> list[str]:
    """One shortlisted candidate as spreadsheet cells, free text through the formula guard."""
    return [
        "" if rank is None else str(rank),
        spreadsheet_cell(candidate.name or ""),
        spreadsheet_cell(candidate.email or ""),
        "" if candidate.score is None else str(round(candidate.score)),
        spreadsheet_cell(_outcome(decision)),
        spreadsheet_cell(decision.rationale or ""),
    ]


async def export_shortlist(
    session: AsyncSession, *, org_id: uuid.UUID, sitting_id: uuid.UUID, actor: Principal
) -> tuple[Iterator[bytes], str]:
    """The shortlist as a CSV stream and its file name; the audit row is written before the first byte."""
    report = await build_sitting_report(session, org_id, sitting_id)
    decisions = await results.decisions_for_sitting(session, org_id, sitting_id)
    listed = ranked_shortlist(report.candidates, decisions)
    await audit.record_for_owner(
        session,
        org_id=org_id,
        actor=actor,
        action="results.shortlist_exported",
        target_type="sitting",
        target_id=str(sitting_id),
        summary=f"Downloaded the shortlist for sitting {sitting_id} as CSV ({len(listed)} candidates)",
    )
    filename = f"{filename_stem(report.sitting.name, report.sitting.id)}-shortlist.csv"
    return stream_csv(SHORTLIST_COLUMNS, (_row(*item) for item in listed)), filename
