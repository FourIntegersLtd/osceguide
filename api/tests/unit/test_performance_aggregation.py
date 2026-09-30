"""Turning a person's marked attempts into the numbers a chart draws.

Each attempt arrives already scored by its own rubric (`_Scored`); this is what
a set of them adds up to. Pass comes from each rubric's own pass line, so a
rubric with none (SCA) has no pass rate rather than an invented one.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.features.dashboard import service_performance as sp
from app.features.dashboard.schemas import DomainScore

DOMAIN_ORDER = ["global_skills", "tasks", "relating_to_others"]
LABELS = {"global_skills": "Global skills", "tasks": "Tasks", "relating_to_others": "Relating to others"}
AT = datetime(2026, 1, 1, tzinfo=UTC)


def scored_domain(
    domain_id: str, fraction: float, *, value: float | None = None, tone: str | None = None
) -> sp._ScoredDomain:
    """One domain of one attempt, as `_score` builds it."""
    return sp._ScoredDomain(
        id=domain_id,
        label=LABELS[domain_id],
        value=value if value is not None else fraction * 100,
        fraction=fraction,
        counts={},
        tone=tone,
    )


def scored(
    fraction: float,
    *,
    passed: bool | None = None,
    domains: tuple[sp._ScoredDomain, ...] = (),
    criticals: int = 0,
) -> sp._Scored:
    """One marked attempt, as `_score` builds it."""
    return sp._Scored(
        at=AT,
        total=fraction * 100,
        fraction=fraction,
        passed=passed,
        criticals=criticals,
        domains=domains,
        version_id="v1",
    )


def test_pass_and_fail_come_from_each_attempt_s_own_pass_line() -> None:
    summary = sp._summary([scored(0.8, passed=True), scored(0.5, passed=False)])
    assert (summary.pass_rate, summary.fail_rate) == (0.5, 0.5)


def test_a_rubric_with_no_pass_line_has_no_pass_rate() -> None:
    """SCA sets no pass line, so none is invented; criticals still count."""
    summary = sp._summary([scored(1.0, criticals=2), scored(0.5)])
    assert (summary.pass_rate, summary.fail_rate, summary.critical_rate) == (None, None, 0.5)


def test_only_judged_attempts_count_toward_pass_and_fail() -> None:
    """An attempt its rubric could not judge is not a fail."""
    summary = sp._summary(
        [scored(1.0, passed=True), scored(1.0, passed=True), scored(0.3, passed=False), scored(0.5)]
    )
    assert summary.pass_rate == round(2 / 3, 4)
    assert summary.pass_rate + summary.fail_rate == 1.0


def test_a_critical_is_an_attempt_with_a_concern_not_a_count_of_concerns() -> None:
    """Three concerns in one consultation is one consultation to talk about."""
    summary = sp._summary([scored(1.0, criticals=3), scored(1.0), scored(0.66), scored(0.66)])
    assert summary.critical_rate == 0.25


def test_domains_are_averaged_across_the_attempts_that_scored_them() -> None:
    marked = [
        scored(0.66, domains=(scored_domain("global_skills", 1.0), scored_domain("tasks", 0.33))),
        scored(0.66, domains=(scored_domain("global_skills", 0.66), scored_domain("tasks", 0.66))),
    ]
    assert sp._domains(marked, DOMAIN_ORDER) == [
        DomainScore(id="global_skills", label="Global skills", score=83.0, value=83.0, counts={}),
        DomainScore(id="tasks", label="Tasks", score=49.5, value=49.5, counts={}),
    ]


def test_a_domain_nobody_was_marked_on_is_left_out() -> None:
    """Unmarked is not the same as bad: a nullable domain that never applied is not a zero."""
    marked = [scored(1.0, domains=(scored_domain("global_skills", 1.0),))]
    assert [domain.id for domain in sp._domains(marked, DOMAIN_ORDER)] == ["global_skills"]


def test_domains_come_back_in_the_rubric_s_own_order() -> None:
    # A radar chart whose axes move between reads is unreadable.
    marked = [
        scored(
            0.66,
            domains=(
                scored_domain("tasks", 1.0),
                scored_domain("relating_to_others", 0.66),
                scored_domain("global_skills", 0.33),
            ),
        )
    ]
    assert [domain.id for domain in sp._domains(marked, DOMAIN_ORDER)] == DOMAIN_ORDER


def test_composition_counts_attempts_by_tone() -> None:
    marked = [
        scored(1.0, domains=(scored_domain("tasks", 1.0, tone="good"),)),
        scored(0.5, domains=(scored_domain("tasks", 0.5, tone="fair"),)),
        scored(0.5, domains=(scored_domain("tasks", 0.5, tone="fair"),)),
    ]
    [tasks] = sp._composition(marked, DOMAIN_ORDER)
    assert tasks.tones == {"good": 1, "fair": 2}
    assert (tasks.green, tasks.amber, tasks.red) == (1, 2, 0)


def test_nothing_marked_is_a_shape_the_dashboard_can_draw() -> None:
    """The empty state is the same shape as an answer, with no rates to show."""
    empty = sp._empty("sca", None)
    assert empty.exam_code == "sca"
    assert empty.domains == []
    assert empty.trend == []
    assert (empty.summary.pass_rate, empty.summary.fail_rate, empty.summary.critical_rate) == (
        None,
        None,
        0.0,
    )
