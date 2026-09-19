"""How somebody is doing: per domain, overall, and over time.

The charts on the consumer exam dashboard. `service.py` answers "what do I have
access to and where did I leave off"; this answers "am I getting better", which
is a different question over a different set of rows — only the marked attempts
at one exam, read back as far as a trend line is worth drawing.

Reading the marking engine's document is `performance.py` and the arithmetic is
`reviews`': an institution ranks its cohort on those numbers and a person's own
dashboard must not quietly use different ones.
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
    """The exam being reported on, however it was named.

    Flattened here because the two ways in hand back different things — a code
    resolves to a catalogue row, an attempt hands back a reference — and the
    rest of this module needs the same four fields either way.
    """

    id: uuid.UUID
    code: str
    rubric_version_id: uuid.UUID | None
    org_id: uuid.UUID | None


async def build(session: AsyncSession, user_id: uuid.UUID, *, exam_code: str | None) -> Performance:
    """The performance charts for one exam, or the empty state.

    An exam nobody has been marked at is answered with empty lists rather than
    a 404: the dashboard has an empty state for "no results yet" and should not
    have to read a refusal to find it.
    """
    exam = await _exam(session, user_id, exam_code)
    if exam is None:
        return _empty(exam_code)

    attempts = await attempts_reads.evaluated_for_user(
        session, user_id, exam_id=exam.id, limit=TREND_LIMIT
    )
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
        trend=[TrendPoint(date=m.at, score=round(m.score, 1)) for m in marked],
    )


@dataclass(frozen=True)
class _Scored:
    at: datetime
    score: float
    domains: Mapping[str, float]
    criticals: int


async def _exam(session: AsyncSession, user_id: uuid.UUID, exam_code: str | None) -> _Exam | None:
    """Which exam to report on: the one asked for, or the last one attempted.

    The default is the most recent attempt of any kind, not the most recent
    marked one, so this screen opens on the same exam as the rest of the
    dashboard — if that attempt is still being marked the answer is the empty
    state, which is the truth about it.

    A code that names no exam is refused by `catalog` as `unknown_exam`; that
    is a client naming something that does not exist, which is not the same as
    an exam with nothing marked yet.
    """
    if exam_code is not None:
        row = await catalog.resolve_exam(session, exam_code)
        return _Exam(id=row.id, code=row.code, rubric_version_id=row.rubric_version_id, org_id=row.org_id)

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

    The marking snapshot rather than a read of the rubric: it is the shape the
    engine was given, so the domain ids in it are the keys the result document
    actually uses.
    """
    if exam.rubric_version_id is None:
        return None
    snapshot = await rubrics.marking_snapshot(
        session, exam.org_id, rubric_version_id=exam.rubric_version_id
    )
    framework = snapshot.get("framework")
    return framework if isinstance(framework, Mapping) else None


async def _score(
    session: AsyncSession,
    user_id: uuid.UUID,
    attempt: attempts_reads.AttemptRef,
    structure: Mapping[str, Any] | None,
) -> _Scored | None:
    """One attempt's marking, or None if there is nothing scorable in it.

    The latest result, not the first: an attempt re-marked under a new policy
    version keeps both, and the chart should show what it says now.
    """
    results = await attempts_reads.read_results(session, attempt.id, requester_id=user_id, is_admin=False)
    if not results:
        return None
    payload = results[-1].payload
    domains = performance.domain_scores(payload, structure)
    score = performance.attempt_score(domains)
    if score is None:
        return None
    return _Scored(
        # When it was sat, falling back to when it was created: an attempt
        # imported from the legacy backend may have no completion time.
        at=attempt.completed_at or attempt.created_at,
        score=score,
        domains=domains,
        criticals=performance.critical_count(payload, structure),
    )


def _summary(marked: Sequence[_Scored]) -> PerformanceSummary:
    total = len(marked)
    passes = sum(1 for m in marked if m.score >= PASS_SCORE)
    criticals = sum(1 for m in marked if m.criticals)
    return PerformanceSummary(
        pass_rate=round(passes / total, 4),
        fail_rate=round((total - passes) / total, 4),
        critical_rate=round(criticals / total, 4),
    )


def _domains(marked: Sequence[_Scored], structure: Mapping[str, Any] | None) -> list[DomainScore]:
    """Each domain averaged across the attempts that were marked on it.

    In the rubric's own order, and a domain no attempt scored is left out
    rather than shown as a zero — unmarked is not the same as bad.
    """
    labels = performance.domain_labels(structure)
    out: list[DomainScore] = []
    for domain_id in performance.scored_domain_ids(structure):
        scores = [m.domains[domain_id] for m in marked if domain_id in m.domains]
        if not scores:
            continue
        out.append(
            DomainScore(
                id=domain_id,
                label=labels.get(domain_id, domain_id),
                score=round(sum(scores) / len(scores), 1),
            )
        )
    return out


def _empty(exam_code: str | None) -> Performance:
    """Nothing marked yet: the shape the dashboard draws its empty state from."""
    return Performance(
        exam_code=exam_code,
        summary=PerformanceSummary(pass_rate=0.0, fail_rate=0.0, critical_rate=0.0),
        domains=[],
        trend=[],
    )
