"""Reporting across sittings: a projection of figures other slices already hold."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service_programmes
from app.features.dashboard.schemas_reporting import OrgReporting, ProgrammeReportRow, StationReportRow
from app.features.results import service as results
from app.features.reviews import service_summary as reviews
from app.features.roster import service as roster
from app.features.sittings import service_reads as sittings
from app.features.stations import service_reads as stations

_MOST_PROGRAMMES = 200


async def build_org_reporting(session: AsyncSession, org_id: uuid.UUID) -> OrgReporting:
    """Per programme: sittings, candidates and the pass rate of released decisions."""
    programmes, _ = await service_programmes.list_programmes(
        session, org_id, limit=_MOST_PROGRAMMES, cursor=None
    )
    figures = await sittings.programme_figures(
        session, org_id, outcomes_by_sitting=await results.released_outcomes_by_sitting(session, org_id)
    )
    rows: list[ProgrammeReportRow] = []
    for programme in programmes:
        figure = figures.get(programme.id, sittings.ProgrammeFigures(0, 0, 0, 0))
        rows.append(
            ProgrammeReportRow(
                programme_id=programme.id,
                exam_id=programme.exam_id,
                exam_name=programme.exam_name,
                sittings=figure.sittings,
                candidates=figure.candidates,
                released=figure.released,
                passed=figure.passed,
                pass_rate=round(100 * figure.passed / figure.released, 1) if figure.released else None,
            )
        )
    return OrgReporting(
        programmes=rows,
        stations=await _station_rows(session, org_id),
        assessors_marking=await reviews.assessors_marking(session, org_id),
    )


async def _station_rows(session: AsyncSession, org_id: uuid.UUID) -> list[StationReportRow]:
    """Each station's pass rate and weakest domain over the stations of released candidates."""
    slots: list[sittings.SlotRef] = []
    for sitting_id, released in (await results.released_candidates(session, org_id)).items():
        sitting_slots = await sittings.slots_for_sitting(session, org_id, sitting_id)
        by_user = await roster.trainees_by_user_id(
            session, org_id, sorted({slot.trainee_id for slot in sitting_slots})
        )
        slots += [
            slot
            for slot in sitting_slots
            if slot.trainee_id in by_user and by_user[slot.trainee_id].id in released
        ]
    if not slots:
        return []
    outcomes = await reviews.outcomes_for_slots(session, org_id, [slot.id for slot in slots])
    titles = await stations.summaries_by_version_id(
        session, org_id, [slot.station_version_id for slot in slots]
    )
    grouped: dict[uuid.UUID, list[reviews.SlotOutcome]] = {}
    for slot in slots:
        outcome = outcomes[slot.id]
        if slot.station_version_id in titles and (outcome.score is not None or outcome.passed is not None):
            grouped.setdefault(titles[slot.station_version_id].station_id, []).append(outcome)
    title_of = {summary.station_id: summary.title for summary in titles.values()}
    rows = [_station_row(title_of[station_id], group) for station_id, group in grouped.items()]
    return sorted(rows, key=lambda row: (row.pass_rate is None, row.pass_rate or 0.0, row.station_title))


def _station_row(title: str, group: list[reviews.SlotOutcome]) -> StationReportRow:
    """One station's line: how many passed, and the domain candidates scored lowest on."""
    judged = [outcome.passed for outcome in group if outcome.passed is not None]
    by_domain: dict[str, list[float]] = {}
    for outcome in group:
        for domain_title, score in outcome.domain_scores.items():
            by_domain.setdefault(domain_title, []).append(score)
    weakest = min(
        by_domain, key=lambda name: (sum(by_domain[name]) / len(by_domain[name]), name), default=None
    )
    return StationReportRow(
        station_title=title,
        assessed=len(group),
        pass_rate=round(100 * sum(judged) / len(judged), 1) if judged else None,
        weakest_competency=weakest,
    )
