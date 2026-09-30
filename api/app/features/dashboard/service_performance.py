"""How somebody is doing at one exam: per domain, overall, and over time.

Only the marked attempts at that exam, each scored by the rubric frozen on it
(`attempts.service_feedback`, `rubrics.scoring`): its native domain values,
total, pass and critical concerns. Trends and domain bars compare the share of
the maximum, so attempts marked under different rubric versions sit on one
chart; pass lines and labels come from the exam's current rubric, and
`mixed_versions` says when more than one version is behind the numbers.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_feedback as attempts_feedback
from app.features.attempts import service_reads as attempts_reads
from app.features.catalog import service as catalog
from app.features.dashboard.schemas import (
    DomainComposition,
    DomainScore,
    Performance,
    PerformanceSummary,
    TrendPoint,
)
from app.features.rubrics import service_marking as rubrics
from app.features.rubrics import service_scoring as scoring

# How far back the trend goes. A line is read for its shape, not for its
# thousandth point, and each attempt costs a read of its result document.
TREND_LIMIT = 50

# Which composition bucket each display tone falls in, until platform-web reads `tones` (Stage 3).
_LEGACY_BUCKET_FOR_TONE = {"poor": "red", "fair": "amber", "good": "green", "excellent": "green"}


@dataclass(frozen=True)
class _Exam:
    """The exam being reported on, however it was named."""

    id: uuid.UUID
    code: str
    rubric_version_id: uuid.UUID | None
    org_id: uuid.UUID | None


@dataclass(frozen=True)
class _ScoredDomain:
    """One domain of one marked attempt, in that attempt's own rubric."""

    id: str
    label: str
    value: float | None
    # 0..1 of the domain's maximum.
    fraction: float | None
    counts: dict[str, int]
    # The display tone that fraction falls in, by the attempt's own rubric.
    tone: str | None


@dataclass(frozen=True)
class _Scored:
    """One marked attempt, scored by the rubric frozen on it."""

    at: datetime
    total: float | None
    # 0..1 of the station maximum: what the trend and cross-version comparisons use.
    fraction: float
    passed: bool | None
    criticals: int
    domains: tuple[_ScoredDomain, ...]
    version_id: str | None


async def build(session: AsyncSession, user_id: uuid.UUID, *, exam_code: str | None) -> Performance:
    """The performance charts for one exam, or the empty state if nothing is marked yet."""
    exam = await _exam(session, user_id, exam_code)
    if exam is None:
        return _empty(exam_code, None)

    current = await _current_rubric(session, exam)
    attempts = await attempts_reads.evaluated_for_user(session, user_id, exam_id=exam.id, limit=TREND_LIMIT)
    oldest_first = list(reversed(attempts))  # the trend is read left to right
    sat_at = {attempt.id: attempt.completed_at or attempt.created_at for attempt in oldest_first}
    marked = [
        scored
        for scored_result in await attempts_feedback.latest_scored(
            session, [attempt.id for attempt in oldest_first]
        )
        if (scored := _score(scored_result, sat_at[scored_result.attempt_id])) is not None
    ]
    if not marked:
        return _empty(exam.code, current)

    domain_order = [section.id for section in current.structure.domains] if current else []
    versions = {scored.version_id for scored in marked}
    return Performance(
        exam_code=exam.code,
        summary=_summary(marked),
        domains=_domains(marked, domain_order),
        trend=[
            TrendPoint(
                date=scored.at,
                score=round(scored.fraction * 100, 1),
                total=None if scored.total is None else round(scored.total, 2),
                passed=scored.passed,
            )
            for scored in marked
        ],
        composition=_composition(marked, domain_order),
        display=current.display if current else None,
        rating=rubrics.rating_read(current.structure) if current else None,
        mixed_versions=len(versions) > 1,
        rubric_versions=len(versions),
    )


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


async def _current_rubric(session: AsyncSession, exam: _Exam) -> rubrics.ScoringRubric | None:
    """The exam's current rubric: its pass lines, labels and domain order are what the charts draw."""
    if exam.rubric_version_id is None:
        return None
    return await rubrics.scoring_rubric_for_version(session, exam.org_id, exam.rubric_version_id)


def _score(scored_result: attempts_feedback.ScoredResult, at: datetime) -> _Scored | None:
    """One attempt's numbers by its own rubric, or None if nothing in it is scorable."""
    scoring_rubric = scored_result.rubric
    display = scoring_rubric.display
    totals = scoring.result_totals(scoring_rubric.structure, display, scored_result.payload)
    if totals.fraction is None:
        return None
    domains: list[_ScoredDomain] = []
    for domain_total in totals.domains:
        fraction = scoring.domain_fraction(display, domain_total.value)
        domains.append(
            _ScoredDomain(
                id=domain_total.id,
                label=domain_total.label,
                value=domain_total.value,
                fraction=fraction,
                counts=dict(domain_total.counts),
                tone=scoring.tone_for_fraction(display, fraction),
            )
        )
    return _Scored(
        # When it was sat, falling back to when it was created: an attempt
        # imported from the legacy backend may have no completion time.
        at=at,
        total=totals.total,
        fraction=totals.fraction,
        passed=totals.passed,
        criticals=totals.critical_count,
        domains=tuple(domains),
        version_id=scoring_rubric.version_id,
    )


def _summary(marked: Sequence[_Scored]) -> PerformanceSummary:
    """The pass, fail and critical rates across every marked attempt.

    Pass and fail count only attempts the rubric could judge: with no pass
    line (SCA) both are null rather than an invented bar. A critical is an
    attempt with at least one concern, not a count of concerns.
    """
    total = len(marked)
    judged = [scored for scored in marked if scored.passed is not None]
    criticals = sum(1 for scored in marked if scored.criticals)
    if not judged:
        return PerformanceSummary(pass_rate=None, fail_rate=None, critical_rate=round(criticals / total, 4))
    passes = sum(1 for scored in judged if scored.passed)
    return PerformanceSummary(
        pass_rate=round(passes / len(judged), 4),
        fail_rate=round((len(judged) - passes) / len(judged), 4),
        critical_rate=round(criticals / total, 4),
    )


def _ordered_domain_ids(marked: Sequence[_Scored], domain_order: Sequence[str]) -> list[str]:
    """Every domain any attempt answered: the current rubric's order first, then the rest as met."""
    seen = [domain.id for scored in marked for domain in scored.domains]
    ordered = [domain_id for domain_id in domain_order if domain_id in seen]
    for domain_id in seen:
        if domain_id not in ordered:
            ordered.append(domain_id)
    return ordered


def _latest_label(marked: Sequence[_Scored], domain_id: str) -> str:
    """A domain's label as the most recent attempt's rubric names it."""
    for scored in reversed(marked):
        for domain in scored.domains:
            if domain.id == domain_id:
                return domain.label
    return domain_id


def _domains(marked: Sequence[_Scored], domain_order: Sequence[str]) -> list[DomainScore]:
    """Each domain averaged across the attempts marked on it.

    A domain no attempt answered (a nullable Ortho domain, say) is left out
    rather than shown as a zero — unmarked is not bad.
    """
    domain_scores: list[DomainScore] = []
    for domain_id in _ordered_domain_ids(marked, domain_order):
        answered = [domain for scored in marked for domain in scored.domains if domain.id == domain_id]
        fractions = [domain.fraction for domain in answered if domain.fraction is not None]
        values = [domain.value for domain in answered if domain.value is not None]
        if not fractions:
            continue
        counts: dict[str, int] = {}
        for domain in answered:
            for scale_value, count in domain.counts.items():
                counts[scale_value] = counts.get(scale_value, 0) + count
        domain_scores.append(
            DomainScore(
                id=domain_id,
                label=_latest_label(marked, domain_id),
                score=round(100 * sum(fractions) / len(fractions), 1),
                value=round(sum(values) / len(values), 2) if values else None,
                counts=counts,
            )
        )
    return domain_scores


def _composition(marked: Sequence[_Scored], domain_order: Sequence[str]) -> list[DomainComposition]:
    """Each domain's attempts, counted by the tone its value fell in."""
    compositions: list[DomainComposition] = []
    for domain_id in _ordered_domain_ids(marked, domain_order):
        tones: dict[str, int] = {}
        for scored in marked:
            for domain in scored.domains:
                if domain.id == domain_id and domain.tone is not None:
                    tones[domain.tone] = tones.get(domain.tone, 0) + 1
        if not tones:
            continue
        buckets = {"red": 0, "amber": 0, "green": 0}
        for tone, count in tones.items():
            bucket = _LEGACY_BUCKET_FOR_TONE.get(tone)
            if bucket is not None:
                buckets[bucket] += count
        compositions.append(
            DomainComposition(
                id=domain_id,
                label=_latest_label(marked, domain_id),
                tones=tones,
                red=buckets["red"],
                amber=buckets["amber"],
                green=buckets["green"],
            )
        )
    return compositions


def _empty(exam_code: str | None, current: rubrics.ScoringRubric | None) -> Performance:
    """Nothing marked yet: the shape the dashboard draws its empty state from."""
    return Performance(
        exam_code=exam_code,
        summary=PerformanceSummary(pass_rate=None, fail_rate=None, critical_rate=0.0),
        domains=[],
        trend=[],
        display=current.display if current else None,
        rating=rubrics.rating_read(current.structure) if current else None,
    )
