"""Assembling the sitting report. A projection: reads services, owns nothing."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts
from app.features.dashboard.errors import SittingNotFound
from app.features.dashboard.schemas_org import ConsoleSitting
from app.features.dashboard.schemas_report import (
    CandidateReport,
    DecisionSummary,
    ReportTotals,
    SittingReport,
    StationReport,
)
from app.features.identity import service as identity
from app.features.results import service as results
from app.features.results import service_evidence
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.rubrics import service_marking as rubrics
from app.features.rubrics import service_scoring as scoring
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations


async def build_sitting_report(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> SittingReport:
    """The whole sitting, per candidate: stations sat, marking, reviewers' ratings and decision status."""
    detail = await sittings.sitting_detail(session, org_id, sitting_id)
    if detail is None:
        raise SittingNotFound()

    slots = [(circuit, slot) for circuit in detail.circuits for slot in circuit.slots]
    user_ids = sorted({slot.trainee_id for _, slot in slots}, key=str)
    slots_by_user: dict[uuid.UUID, list[tuple[sittings.CircuitDetail, sittings.SlotRef]]] = {}
    for circuit, slot in slots:
        slots_by_user.setdefault(slot.trainee_id, []).append((circuit, slot))
    people = await identity.user_refs_by_ids(session, user_ids)
    trainees = await roster.trainees_by_user_id(session, org_id, user_ids)
    titles = await stations.summaries_by_version_id(
        session, org_id, [slot.station_version_id for _, slot in slots]
    )
    live = await attempts.live_attempts_for_slots(session, [slot.id for _, slot in slots])
    decisions = await results.decisions_for_sitting(session, org_id, sitting_id)
    summaries = await reviews.summaries_for_slots(session, org_id, [slot.id for _, slot in slots])
    outcomes = await reviews.outcomes_for_slots(session, org_id, [slot.id for _, slot in slots])
    scoring_rubric = await rubrics.scoring_rubric_for_version(
        session, org_id, detail.sitting.rubric_version_id
    )

    candidates: list[CandidateReport] = []
    for user_id in user_ids:
        station_reports: list[StationReport] = []
        for circuit, slot in slots_by_user[user_id]:
            summary = summaries[slot.id]
            outcome = outcomes[slot.id]
            attempt = live.get(slot.id)
            title = titles.get(slot.station_version_id)
            marked = service_evidence.station_is_marked(
                attempt is not None and attempt.status == "evaluated", summary.overall_rag
            )
            station_reports.append(
                StationReport(
                    slot_id=slot.id,
                    circuit_id=circuit.circuit.id,
                    circuit_name=circuit.circuit.name,
                    slot_index=slot.slot_index,
                    station_title=title.title if title else None,
                    slot_status=slot.status,
                    attempt_id=attempt.id if attempt else None,
                    attempt_status=attempt.status if attempt else None,
                    marked=marked,
                    absent=slot.status == "skipped" and not marked,
                    overall_rag=summary.overall_rag,
                    by_domain=dict(summary.by_domain),
                    score=outcome.score,
                    passed=outcome.passed,
                )
            )
        person = people.get(user_id)
        trainee = trainees.get(user_id)
        decision = decisions.get(trainee.id) if trainee else None
        shown_name, shown_email = roster.shown_identity(trainee, person)
        candidates.append(
            CandidateReport(
                user_id=user_id,
                trainee_id=trainee.id if trainee else None,
                name=shown_name,
                email=shown_email,
                stations=station_reports,
                stations_marked=sum(1 for station_report in station_reports if station_report.marked),
                overall_rag=scoring.worst_rating(
                    scoring_rubric.structure,
                    [station_report.overall_rag for station_report in station_reports],
                ),
                score=_mean([station_report.score for station_report in station_reports]),
                stations_passed=sum(1 for station_report in station_reports if station_report.passed is True),
                decision=DecisionSummary(
                    workflow_state=decision.workflow_state,
                    assessment_outcome=decision.assessment_outcome,
                    recruitment_outcome=decision.recruitment_outcome,
                    signed_off_at=decision.signed_off_at,
                    released_at=decision.released_at,
                    signed_off_by_name=decision.signed_off_by_name,
                )
                if decision
                else None,
            )
        )

    return SittingReport(
        sitting=ConsoleSitting(
            id=detail.sitting.id,
            name=detail.sitting.name,
            mode=detail.sitting.mode,
            sitting_type=detail.sitting.sitting_type,
            status=detail.sitting.status,
            scheduled_for=detail.sitting.scheduled_for,
            rubric_version_id=detail.sitting.rubric_version_id,
        ),
        rating=rubrics.rating_read(scoring_rubric.structure),
        totals=ReportTotals(
            candidates=len(candidates),
            stations=sum(
                1 for candidate in candidates for station in candidate.stations if not station.absent
            ),
            stations_marked=sum(candidate.stations_marked for candidate in candidates),
            awaiting_marking=sum(
                1
                for candidate in candidates
                if any(
                    station.slot_status == "completed" and not station.marked
                    for station in candidate.stations
                )
            ),
            decisions_released=sum(
                1 for candidate in candidates if candidate.decision and candidate.decision.released_at
            ),
        ),
        candidates=candidates,
    )


def _mean(scores: list[float | None]) -> float | None:
    """The mean of the scores that exist, or None when none do: unmarked is not zero."""
    present = [score for score in scores if score is not None]
    return round(sum(present) / len(present), 1) if present else None
