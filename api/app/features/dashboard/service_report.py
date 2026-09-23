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
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations


async def build_sitting_report(
    session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID
) -> SittingReport:
    detail = await sittings.sitting_detail(session, org_id, sitting_id)
    if detail is None:
        raise SittingNotFound()

    slots = [(circuit, slot) for circuit in detail.circuits for slot in circuit.slots]
    user_ids = sorted({slot.trainee_id for _, slot in slots}, key=str)
    people = await identity.user_refs_by_ids(session, user_ids)
    trainees = await roster.trainees_by_user_id(session, org_id, user_ids)
    titles = await stations.summaries_by_version_id(session, org_id, [s.station_version_id for _, s in slots])
    live = await attempts.live_attempts_for_slots(session, [s.id for _, s in slots])
    decisions = await results.decisions_for_sitting(session, org_id, sitting_id)
    summaries = await reviews.summaries_for_slots(session, org_id, [s.id for _, s in slots])

    candidates: list[CandidateReport] = []
    for user_id in user_ids:
        rows: list[StationReport] = []
        for circuit, slot in slots:
            if slot.trainee_id != user_id:
                continue
            summary = summaries[slot.id]
            attempt = live.get(slot.id)
            title = titles.get(slot.station_version_id)
            rows.append(
                StationReport(
                    slot_id=slot.id,
                    circuit_id=circuit.circuit.id,
                    circuit_name=circuit.circuit.name,
                    slot_index=slot.slot_index,
                    station_title=title.title if title else None,
                    slot_status=slot.status,
                    attempt_id=attempt.id if attempt else None,
                    attempt_status=attempt.status if attempt else None,
                    marked=attempt is not None and attempt.status == "evaluated",
                    overall_rag=summary.overall_rag,
                    by_domain=dict(summary.by_domain),
                )
            )
        person = people.get(user_id)
        trainee = trainees.get(user_id)
        decision = decisions.get(trainee.id) if trainee else None
        candidates.append(
            CandidateReport(
                user_id=user_id,
                trainee_id=trainee.id if trainee else None,
                name=person.name if person else None,
                email=person.email if person else None,
                stations=rows,
                stations_marked=sum(1 for r in rows if r.marked),
                overall_rag=reviews.combine_ratings([r.overall_rag for r in rows]),
                decision=DecisionSummary(
                    workflow_state=decision.workflow_state,
                    assessment_outcome=decision.assessment_outcome,
                    recruitment_outcome=decision.recruitment_outcome,
                    signed_off_at=decision.signed_off_at,
                    released_at=decision.released_at,
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
        totals=ReportTotals(
            candidates=len(candidates),
            stations=len(slots),
            stations_marked=sum(c.stations_marked for c in candidates),
            decisions_released=sum(1 for c in candidates if c.decision and c.decision.released_at),
        ),
        candidates=candidates,
    )
