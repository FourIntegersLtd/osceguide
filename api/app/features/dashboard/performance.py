"""Reading the marking engine's output into ratings, per domain.

The engine writes one document per attempt, shaped by the exam's framework:
`payload[domain_id][competency_id].score`, where a score is R, A or G. The
rubric says which top-level keys are scored domains — a payload also carries
blocks like `actionable_feedback` and `clinical_analysis` that are prose, not
marks, and counting those would drag every domain towards the same number.

Competency ids are deliberately not matched. Ortho prefixes its with the
domain (`clinical_skills_situational_awareness`) because the same competency
appears in four domains, while PLAB does not; reading whatever is inside the
domain block works for both and needs no table mapping one spelling to the
other.

Pure functions over documents. The arithmetic itself is
`reviews/scoring.py` — an institution ranks its cohort on those numbers, and a
person's own dashboard must not quietly use different ones.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.features.reviews import service_summary as reviews

SCORE_KEY = "score"


def scored_domain_ids(structure: Mapping[str, Any] | None) -> list[str]:
    """The domains a rubric marks, in the order it lists them."""
    domains = (structure or {}).get("domains")
    if not isinstance(domains, list):
        return []
    return [d["id"] for d in domains if isinstance(d, Mapping) and isinstance(d.get("id"), str)]


def domain_labels(structure: Mapping[str, Any] | None) -> dict[str, str]:
    """Each domain's human label, falling back to its id."""
    domains = (structure or {}).get("domains")
    if not isinstance(domains, list):
        return {}
    out: dict[str, str] = {}
    for d in domains:
        if not isinstance(d, Mapping):
            continue
        domain_id = d.get("id")
        if isinstance(domain_id, str):
            label = d.get("label")
            out[domain_id] = label if isinstance(label, str) and label else domain_id
    return out


def ratings_by_domain(
    payload: Mapping[str, Any] | None, structure: Mapping[str, Any] | None
) -> dict[str, list[str]]:
    """Every competency rating in this result, grouped by its domain."""
    if not isinstance(payload, Mapping):
        return {}
    out: dict[str, list[str]] = {}
    for domain_id in scored_domain_ids(structure):
        block = payload.get(domain_id)
        if not isinstance(block, Mapping):
            continue
        ratings = [
            competency[SCORE_KEY]
            for competency in block.values()
            if isinstance(competency, Mapping) and isinstance(competency.get(SCORE_KEY), str)
        ]
        if ratings:
            out[domain_id] = ratings
    return out


def domain_scores(payload: Mapping[str, Any] | None, structure: Mapping[str, Any] | None) -> dict[str, float]:
    """One 0–100 score per domain, from the competency ratings inside it.

    The majority rating rather than the mean, which is `reviews/scoring.py`'s
    rule and its reasoning: three greens and a red is a green domain with a red
    competency in it, not an amber domain that describes neither.
    """
    out: dict[str, float] = {}
    for domain_id, ratings in ratings_by_domain(payload, structure).items():
        # A rating outside the vocabulary leaves the domain unscored rather
        # than raising: that is a migration artefact, not a reader's problem.
        score = reviews.score_for_ratings(ratings)
        if score is not None:
            out[domain_id] = score
    return out


def attempt_score(scores: Mapping[str, float]) -> float | None:
    """The attempt's score: the mean of its domains, equally weighted.

    Equal weighting is the institution rule too — a domain with twelve
    competencies counts the same as one with four.
    """
    return reviews.mean_score(list(scores.values()))


def critical_count(payload: Mapping[str, Any] | None, structure: Mapping[str, Any] | None) -> int:
    """How many competencies were rated red.

    Counted across every domain rather than per domain, because that is what
    the summary band reports: one red anywhere is the thing worth seeing.
    """
    return sum(
        1
        for ratings in ratings_by_domain(payload, structure).values()
        for rating in ratings
        if rating.strip().upper() == "R"
    )
