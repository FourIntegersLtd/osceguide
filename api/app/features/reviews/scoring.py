"""Turns reviewers' ratings into the 0-100 scores a cohort is ranked on.

A review's `field_values` is a flat map of paths ending in the rubric's rating
field: `domain.competency.score` rates one competency, `domain.score` the
whole domain (`competent` in place of `score` on a boolean rubric). A rating
is whatever the sitting's rubric rates in: R/A/G, a number, a yes/no.

The rule is the one institutions have always ranked on (oracle:
`b2b-api/tests/test_session_cohort_scoring.py`): a domain is its competencies
combined as one rating (`rubrics.scoring.combine_reviewers`: the majority,
ties downward, for a scale), worth that rating's fraction of the best one out
of 100; the station is the mean of its domains, equally weighted. With R/A/G
that is G 100, A 66 and R 33, exactly as before.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.features.rubrics import service_scoring as scoring


def scores_by_domain(
    structure: scoring.RubricStructure, ratings_by_domain: scoring.DomainRatings
) -> dict[str, float]:
    """One 0-100 score per domain: its ratings combined as one (`combine_reviewers`), as a percent."""
    scores: dict[str, float] = {}
    for domain_id, ratings in ratings_by_domain.items():
        percent = scoring.rating_percent(structure, scoring.combine_reviewers(structure, ratings))
        if percent is not None:
            scores[domain_id] = percent
    return scores


def domain_scores(structure: scoring.RubricStructure, field_values: Mapping[str, object]) -> dict[str, float]:
    """One 0–100 score per domain, from the ratings a review's paths hold.

    Competencies within a domain are equally weighted through the combined
    rating; a domain-level rating (`domain.score`, one segment) counts as a
    rating of that domain like any other.
    """
    return scores_by_domain(structure, scoring.ratings_from_paths(structure, field_values))


def station_score(scores: Mapping[str, float]) -> float | None:
    """The station's score: the mean of its domains, equally weighted.

    A domain with twelve skills counts the same as one with two.
    """
    if not scores:
        return None
    return sum(scores.values()) / len(scores)


def effective_ratings(
    structure: scoring.RubricStructure, marked: Mapping[str, object], reviewed: Mapping[str, object]
) -> dict[str, list[scoring.RatingValue]]:
    """The ratings left standing once a GP lead has had their say, grouped by domain.

    Two kinds of override: a **competency** rating (`domain.skill.score`) is
    laid over the marking, so one changed skill may not move the domain at
    all; a **domain** rating (`domain.score`) replaces the domain outright and
    stands for every competency in it, which is what `passed` then counts.
    """
    overlaid: dict[str, object] = dict(marked)
    domain_level: dict[str, object] = {}
    for path, rating in reviewed.items():
        parts = scoring.rating_path_parts(structure, path)
        if parts is None:
            continue
        if len(parts) == 1:
            domain_level[parts[0]] = rating
        else:
            overlaid[path] = rating

    effective = scoring.ratings_from_paths(structure, overlaid)
    competency_counts = {section.id: len(section.competencies) for section in structure.domains}
    for domain_id, rating in domain_level.items():
        if scoring.is_valid_rating(structure.rating, rating):
            standing = cast(scoring.RatingValue, rating)
            effective[domain_id] = [standing] * max(competency_counts.get(domain_id, 0), 1)
    return effective


def apply_review_overrides(
    structure: scoring.RubricStructure, marked: Mapping[str, object], reviewed: Mapping[str, object]
) -> dict[str, float]:
    """The domain scores after a GP lead has had their say (see `effective_ratings`)."""
    return scores_by_domain(structure, effective_ratings(structure, marked, reviewed))


def review_priority(*, completion_rate: float, assessment_score: float | None) -> str:
    """Which candidates a GP lead should look at first.

    An unfinished examination outranks a poor score: a candidate who sat half
    the stations has a problem nobody has looked at yet.
    """
    if completion_rate < 0.5:
        return "urgent"
    score = assessment_score if assessment_score is not None else 0.0
    if completion_rate < 1.0 or score < 60.0:
        return "high"
    if score >= 80.0 and completion_rate >= 1.0:
        return "low"
    return "standard"
