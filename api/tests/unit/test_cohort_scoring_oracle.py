"""Oracle: `b2b-api/tests/test_session_cohort_scoring.py`.

The arithmetic an institution ranks its candidates on. Ported because these
numbers *are* the product: a GP lead decides who to look at first from them,
and a rounding difference or a changed weighting moves a real candidate up or
down a list somebody acts on.

Every case below is the legacy case, with the product vocabulary stripped and
the shape changed from b2b's nested feedback blobs to this platform's flat
`domain.skill.score` field values. The rubric is the seeded SCA one: its R/A/G
rating is what the legacy numbers were written against, and since Stage 2 the
arithmetic reads the rating from the rubric instead of assuming it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.features.reviews.scoring import (
    apply_review_overrides,
    domain_scores,
    review_priority,
    station_score,
)
from app.features.rubrics import domain as rubric_domain
from app.features.rubrics import service_scoring as rubric_scoring

_SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())
STRUCTURE = rubric_domain.parse_structure(
    next(entry["rubric"]["structure"] for entry in _SEED["exams"] if entry["code"] == "sca")
)


def test_the_three_ratings_are_worth_what_they_were_worth() -> None:
    """Oracle: `_RAG_SCORES`. Not evenly spaced; an amber sits nearer a green."""
    assert [rubric_scoring.rating_percent(STRUCTURE, value) for value in ("G", "A", "R")] == [
        100.0,
        66.0,
        33.0,
    ]
    assert rubric_scoring.rating_percent(STRUCTURE, rubric_scoring.normalise_rating(STRUCTURE, "g")) == 100.0
    assert rubric_scoring.rating_percent(STRUCTURE, rubric_scoring.normalise_rating(STRUCTURE, " A ")) == 66.0
    assert rubric_scoring.rating_percent(STRUCTURE, "X") is None


def test_a_domain_takes_the_majority_of_its_skills() -> None:
    """Oracle: `test_extract_rag_score_from_nested_feedback`, in the new shape."""
    scores = domain_scores(
        STRUCTURE,
        {
            "global_skills.structures_consultation.score": "G",
            "global_skills.avoids_repetition.score": "G",
            "global_skills.safety_net.score": "R",
        },
    )
    assert scores == {"global_skills": 100.0}


def test_a_tie_between_reviewers_resolves_downward() -> None:
    """Oracle: `_TIE_BREAK_ORDER`. The worse rating is the one worth a conversation."""
    assert rubric_scoring.combine_reviewers(STRUCTURE, ["G", "R"]) == "R"
    assert rubric_scoring.combine_reviewers(STRUCTURE, ["G", "A"]) == "A"
    assert rubric_scoring.combine_reviewers(STRUCTURE, ["G", "G", "A", "A", "R"]) == "A"
    assert rubric_scoring.combine_reviewers(STRUCTURE, []) is None
    assert rubric_scoring.combine_reviewers(STRUCTURE, ["not a rating"]) is None


def test_domains_are_equally_weighted_and_the_station_is_their_mean() -> None:
    """Oracle: `test_domain_scores_are_equal_weighted`, including its 66.5."""
    field_values = {
        "global_skills.structure.score": "G",
        "global_skills.rapport.score": "G",
        "tasks.safety_net.score": "R",
    }
    scores = domain_scores(STRUCTURE, field_values)
    assert scores == {"global_skills": 100.0, "tasks": 33.0}
    assert station_score(scores) == 66.5


def test_a_station_nobody_rated_has_no_score_rather_than_a_zero() -> None:
    """A zero would rank an unmarked candidate below a failing one."""
    assert station_score({}) is None
    assert domain_scores(STRUCTURE, {"notes": "no ratings here"}) == {}


def test_a_skill_review_recalculates_the_domain_it_is_in() -> None:
    """Oracle: `test_skill_review_overlays_recalculate_domain_average`.

    One changed skill may not move the domain at all — that is the point of
    overlaying and recomputing rather than replacing. An even split *does* move
    it, downward, which is the tie-break above doing its job.
    """
    marked = {
        "global_skills.uses_clear_language.score": "G",
        "global_skills.avoids_repetition.score": "G",
        "global_skills.structures_consultation.score": "G",
        "tasks.safety_net.score": "A",
    }
    # One skill dropped to amber, and the domain does not move: two greens
    # still outnumber it. A reviewer disagreeing about one skill has not
    # re-rated the domain, and the arithmetic says so.
    unchanged = apply_review_overrides(STRUCTURE, marked, {"global_skills.avoids_repetition.score": "A"})
    assert unchanged["global_skills"] == 100.0
    assert unchanged["tasks"] == 66.0

    # Two of the three, and now it does.
    moved = apply_review_overrides(
        STRUCTURE,
        marked,
        {
            "global_skills.avoids_repetition.score": "R",
            "global_skills.uses_clear_language.score": "R",
        },
    )
    assert moved["global_skills"] == 33.0


def test_a_domain_review_replaces_the_domain_outright() -> None:
    """A reviewer who rates the domain has judged the whole of it."""
    marked = {
        "global_skills.uses_clear_language.score": "G",
        "global_skills.avoids_repetition.score": "G",
    }
    assert apply_review_overrides(STRUCTURE, marked, {"global_skills.score": "R"}) == {"global_skills": 33.0}


def test_a_domain_review_wins_over_a_skill_review_of_the_same_domain() -> None:
    marked = {"tasks.safety_net.score": "G"}
    overridden = apply_review_overrides(
        STRUCTURE, marked, {"tasks.safety_net.score": "G", "tasks.score": "A"}
    )
    assert overridden == {"tasks": 66.0}


def test_reviewing_nothing_leaves_the_marking_alone() -> None:
    marked = {"tasks.safety_net.score": "A"}
    assert (
        apply_review_overrides(STRUCTURE, marked, {}) == domain_scores(STRUCTURE, marked) == {"tasks": 66.0}
    )


@pytest.mark.parametrize(
    ("completion_rate", "assessment_score", "band"),
    [
        (0.4, 90.0, "urgent"),
        (0.9, 55.0, "high"),
        (1.0, 85.0, "low"),
        (1.0, 70.0, "standard"),
    ],
)
def test_the_review_priority_bands(completion_rate: float, assessment_score: float, band: str) -> None:
    """Oracle: `test_review_priority_bands`, every case.

    Note the first: 90 is a good score and it is still urgent, because the
    candidate sat fewer than half the stations and nobody has looked at why.
    """
    assert review_priority(completion_rate=completion_rate, assessment_score=assessment_score) == band


def test_an_unscored_candidate_is_treated_as_scoring_nothing_for_ranking() -> None:
    """Oracle: `score = assessment_score if assessment_score is not None else 0.0`.

    Deliberate, and worth reading twice: a complete examination nobody has
    marked ranks as `high` priority, which is what gets it marked.
    """
    assert review_priority(completion_rate=1.0, assessment_score=None) == "high"
    assert review_priority(completion_rate=0.2, assessment_score=None) == "urgent"
