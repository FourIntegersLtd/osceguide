"""Turning a person's marked attempts into the numbers a chart draws.

The extraction is pinned next door in `test_performance_extraction.py`; this is
the other half — what a set of scored attempts adds up to, and what "pass"
means when no rubric carries a pass mark.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.features.dashboard import service_performance as sp
from app.features.reviews import service_summary as reviews

STRUCTURE = {
    "domains": [
        {"id": "global_skills", "label": "Global skills"},
        {"id": "tasks", "label": "Tasks"},
        {"id": "relating_to_others", "label": "Relating to others"},
    ]
}
AT = datetime(2026, 1, 1, tzinfo=UTC)


def scored(score: float, *, domains: dict[str, float] | None = None, criticals: int = 0) -> sp._Scored:
    return sp._Scored(at=AT, score=score, domains=domains or {}, criticals=criticals)


def test_the_pass_mark_is_the_amber_score() -> None:
    """Stated once, and tied to the scale it came from.

    No seeded rubric carries a pass mark, so this is the platform's reading of
    one: an attempt passes when it averages at least an amber. Pinned against
    `reviews` so that changing what an A is worth cannot silently move what a
    pass is.
    """
    assert reviews.score_for_ratings(["A"]) == sp.PASS_SCORE


def test_an_attempt_exactly_on_the_mark_passes() -> None:
    # At or above, not above: a straight amber is adequate everywhere, which is
    # not a failure, and a boundary that excluded it would fail every attempt
    # that was never rated green.
    summary = sp._summary([scored(sp.PASS_SCORE), scored(sp.PASS_SCORE - 0.1)])
    assert summary.pass_rate == 0.5
    assert summary.fail_rate == 0.5


def test_passes_and_fails_account_for_every_marked_attempt() -> None:
    """The two rates sum to one, so the chart's bands never leave a gap.

    An attempt with nothing scorable in it is not counted as a fail; it never
    reaches here at all, because `_score` drops it.
    """
    summary = sp._summary([scored(100.0), scored(100.0), scored(33.0)])
    assert summary.pass_rate + summary.fail_rate == 1.0
    assert summary.pass_rate == round(2 / 3, 4)


def test_a_critical_is_an_attempt_with_a_red_not_a_count_of_reds() -> None:
    """Three reds in one consultation is one consultation to talk about.

    Rated separately from pass and fail because a passing attempt can still
    hold a red competency, and that is the thing worth seeing.
    """
    summary = sp._summary([scored(100.0, criticals=3), scored(100.0), scored(66.0), scored(66.0)])
    assert summary.critical_rate == 0.25
    assert summary.pass_rate == 1.0


def test_domains_are_averaged_across_the_attempts_that_scored_them() -> None:
    marked = [
        scored(66.5, domains={"global_skills": 100.0, "tasks": 33.0}),
        scored(66.0, domains={"global_skills": 66.0, "tasks": 66.0}),
    ]
    assert sp._domains(marked, STRUCTURE) == [
        sp.DomainScore(id="global_skills", label="Global skills", score=83.0),
        sp.DomainScore(id="tasks", label="Tasks", score=49.5),
    ]


def test_a_domain_nobody_was_marked_on_is_left_out() -> None:
    """Unmarked is not the same as bad.

    A rubric's third domain shown as a zero reads as a failure at it, when in
    fact no station this person sat asked about it.
    """
    marked = [scored(100.0, domains={"global_skills": 100.0})]
    assert [d.id for d in sp._domains(marked, STRUCTURE)] == ["global_skills"]


def test_domains_come_back_in_the_rubric_s_own_order() -> None:
    # Not alphabetical and not whatever the payload happened to list: a radar
    # chart whose axes move between reads is unreadable.
    marked = [scored(100.0, domains={"tasks": 100.0, "relating_to_others": 66.0, "global_skills": 33.0})]
    assert [d.id for d in sp._domains(marked, STRUCTURE)] == [
        "global_skills",
        "tasks",
        "relating_to_others",
    ]


def test_nothing_marked_is_a_shape_the_dashboard_can_draw() -> None:
    """The empty state is the same shape as an answer, with zero rates.

    A 404 would make "you have not been marked yet" read as an error, and a
    missing key would make the chart code branch.
    """
    empty = sp._empty("sca")
    assert empty.exam_code == "sca"
    assert empty.domains == []
    assert empty.trend == []
    assert (empty.summary.pass_rate, empty.summary.fail_rate, empty.summary.critical_rate) == (
        0.0,
        0.0,
        0.0,
    )
