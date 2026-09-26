"""How somebody is doing at one exam: per domain, overall, and over time.

Only the marked attempts at that exam. Reading the marking engine's document is
`performance.py`; the pass/fail arithmetic matches `reviews` so an institution's
cohort ranking and a person's own dashboard agree on the same numbers.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_reads as attempts_reads
from app.features.catalog import service as catalog
from app.features.dashboard import performance
from app.features.dashboard.schemas import (
    DomainComposition,
    DomainScore,
    Performance,
    PerformanceSummary,
    TrendPoint,
)
from app.features.rubrics import service_marking as rubrics

# How far back the trend goes. A line is read for its shape, not for its
# thousandth point, and each attempt costs a read of its result document.
TREND_LIMIT = 50

# What "pass" means here. No seeded rubric carries a pass mark, so it is stated
# once rather than left to each chart: an attempt passes when its score is at
# least an amber — `reviews` scores A at 66.0 — which reads as "every domain
# adequate on average". Below that is a fail, and the two rates therefore sum
# to one: a marked attempt is one or the other. A red anywhere is reported
# separately by `critical_rate`, because a passing attempt can still contain a
# competency that needs a conversation.
PASS_SCORE = 66.0


@dataclass(frozen=True)
class _Exam:
    """The exam being reported on, however it was named."""

    id: uuid.UUID
    code: str
    rubric_version_id: uuid.UUID | None
    org_id: uuid.UUID | None


async def build(session: AsyncSession, user_id: uuid.UUID, *, exam_code: str | None) -> Performance:
    """The performance charts for one exam, or the empty state if nothing is marked yet."""
    exam = await _exam(session, user_id, exam_code)
    if exam is None:
        return _empty(exam_code)

    attempts = await attempts_reads.evaluated_for_user(session, user_id, exam_id=exam.id, limit=TREND_LIMIT)
    structure = await _structure(session, exam)
    marked: list[_Scored] = []
    for attempt in reversed(attempts):  # oldest first: the trend is read left to right
        scored = await _score(session, user_id, attempt, structure)
        if scored is not None:
            marked.append(scored)
    if not marked:
        return _empty(exam.code)

    return Performance(
        exam_code=exam.code,
        summary=_summary(marked),
        domains=_domains(marked, structure),
        trend=[TrendPoint(date=scored.at, score=round(scored.score, 1)) for scored in marked],
        composition=_composition(marked, structure),
    )


@dataclass(frozen=True)
class _Scored:
    """One marked attempt's score, its per-domain breakdown and its critical count."""

    at: datetime
    score: float
    domains: Mapping[str, float]
    criticals: int


async def _exam(session: AsyncSession, user_id: uuid.UUID, exam_code: str | None) -> _Exam | None:
    """Which exam to report on: the one asked for, or the last one attempted.

    The default is the most recent attempt of any kind, not the most recent marked one, so
    this screen opens on the same exam as the rest of the dashboard. A code naming no exam
    is refused by `catalog` as `unknown_exam`.
    """
    if exam_code is not None:
        exam_row = await catalog.resolve_exam(session, exam_code)
        return _Exam(
            id=exam_row.id,
            code=exam_row.code,
            rubric_version_id=exam_row.rubric_version_id,
            org_id=exam_row.org_id,
        )

    recent = await attempts_reads.recent_for_user(session, user_id, limit=1)
    if not recent:
        return None
    ref = await catalog.exam_ref_by_id(session, recent[0].exam_id)
    if ref is None:
        return None
    return _Exam(
        id=ref.id,
        code=ref.code,
        # `framework_id` is the rubric version's own id, and empty for an exam
        # that names no rubric — one nothing can have been marked against.
        rubric_version_id=uuid.UUID(ref.framework_id) if ref.framework_id else None,
        org_id=ref.org_id,
    )


async def _structure(session: AsyncSession, exam: _Exam) -> Mapping[str, Any] | None:
    """The rubric's own account of which domains it marks, and their labels.

    The marking snapshot, not a fresh read of the rubric: its domain ids are the keys the
    result document actually uses.
    """
    if exam.rubric_version_id is None:
        return None
    snapshot = await rubrics.marking_snapshot(session, exam.org_id, rubric_version_id=exam.rubric_version_id)
    framework = snapshot.get("framework")
    return framework if isinstance(framework, Mapping) else None


async def _score(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt: attempts_reads.AttemptRef,
    structure: Mapping[str, Any] | None,
) -> _Scored | None:
    """One attempt's marking, or None if there is nothing scorable in it.

    Uses the latest result: a re-marked attempt keeps both, and the chart shows what it says now.
    """
    results = await attempts_reads.read_results(session, attempt.id, requester_id=user_id, is_admin=False)
    if not results:
        return None
    marking_result = results[-1].payload
    domains = performance.domain_scores(marking_result, structure)
    score = performance.attempt_score(domains)
    if score is None:
        return None
    return _Scored(
        # When it was sat, falling back to when it was created: an attempt
        # imported from the legacy backend may have no completion time.
        at=attempt.completed_at or attempt.created_at,
        score=score,
        domains=domains,
        criticals=performance.critical_count(marking_result, structure),
    )


def _summary(marked: Sequence[_Scored]) -> PerformanceSummary:
    """The pass, fail and critical rates across every marked attempt."""
    total = len(marked)
    passes = sum(1 for scored in marked if scored.score >= PASS_SCORE)
    criticals = sum(1 for scored in marked if scored.criticals)
    return PerformanceSummary(
        pass_rate=round(passes / total, 4),
        fail_rate=round((total - passes) / total, 4),
        critical_rate=round(criticals / total, 4),
    )


def _domains(marked: Sequence[_Scored], structure: Mapping[str, Any] | None) -> list[DomainScore]:
    """Each domain averaged across the attempts marked on it.

    A domain no attempt scored is left out rather than shown as a zero — unmarked is not bad.
    """
    labels = performance.domain_labels(structure)
    domain_scores: list[DomainScore] = []
    for domain_id in performance.scored_domain_ids(structure):
        scores = [scored.domains[domain_id] for scored in marked if domain_id in scored.domains]
        if not scores:
            continue
        domain_scores.append(
            DomainScore(
                id=domain_id,
                label=labels.get(domain_id, domain_id),
                score=round(sum(scores) / len(scores), 1),
            )
        )
    return domain_scores


def _band(score: float) -> str:
    """Which of the three traffic-light bands a domain's average score falls in."""
    if score >= 83:
        return "green"
    if score >= 50:
        return "amber"
    return "red"


def _composition(marked: Sequence[_Scored], structure: Mapping[str, Any] | None) -> list[DomainComposition]:
    """Each domain's attempts, split into how many were red, amber or green."""
    labels = performance.domain_labels(structure)
    compositions: list[DomainComposition] = []
    for domain_id in performance.scored_domain_ids(structure):
        counts = {"red": 0, "amber": 0, "green": 0}
        for scored in marked:
            score = scored.domains.get(domain_id)
            if score is None:
                continue
            counts[_band(score)] += 1
        if not any(counts.values()):
            continue
        compositions.append(
            DomainComposition(
                id=domain_id,
                label=labels.get(domain_id, domain_id),
                red=counts["red"],
                amber=counts["amber"],
                green=counts["green"],
            )
        )
    return compositions


def _empty(exam_code: str | None) -> Performance:
    """Nothing marked yet: the shape the dashboard draws its empty state from."""
    return Performance(
        exam_code=exam_code,
        summary=PerformanceSummary(pass_rate=0.0, fail_rate=0.0, critical_rate=0.0),
        domains=[],
        trend=[],
    )
