"""Turns R/A/G ratings into the 0-100 scores a cohort is ranked on.

A review's `field_values` is a flat map of `domain.skill.score` paths; a
rating is one of R, A or G, and nothing in this platform writes a numeric
score.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.features.reviews.domain import RAG_VALUES, InvalidRag, normalize_rag

# Oracle: `_RAG_SCORES`. Not evenly spaced, and deliberately so — an amber is
# nearer a green than a red is to an amber.
RAG_SCORES: Mapping[str, float] = {"G": 100.0, "A": 66.0, "R": 33.0}

# Oracle: `_TIE_BREAK_ORDER`. Worst first: a domain two reviewers split on is
# reported at the lower rating, because that is the one worth a conversation.
TIE_BREAK_ORDER = ("R", "A", "G")

SCORE_SUFFIX = ".score"


def score_for(rag: str) -> float:
    """The 0–100 value of one rating. Raises on anything that is not a rating."""
    return RAG_SCORES[normalize_rag(rag)]


def majority_rag(letters: Sequence[str]) -> str | None:
    """The plurality rating, resolving a tie downward (worst wins).

    Plurality rather than mean: three greens and a red is a green domain with
    a red skill in it, not an amber that describes neither.
    """
    counts = dict.fromkeys(RAG_VALUES, 0)
    for letter in letters:
        try:
            counts[normalize_rag(letter)] += 1
        except InvalidRag:
            continue
    if not any(counts.values()):
        return None
    most = max(counts.values())
    tied = [rag for rag, count in counts.items() if count == most]
    if len(tied) == 1:
        return tied[0]
    return next(rag for rag in TIE_BREAK_ORDER if rag in tied)


def _score_path_parts(path: str) -> list[str] | None:
    """The segments before `.score`, or None if this is not a rating path."""
    if not isinstance(path, str) or not path.endswith(SCORE_SUFFIX):
        return None
    stem = path[: -len(SCORE_SUFFIX)].strip()
    return [part for part in stem.split(".") if part] or None


def domain_scores(field_values: Mapping[str, object]) -> dict[str, float]:
    """One 0–100 score per domain, from the skill ratings inside it.

    Skills within a domain are equally weighted through the majority; a
    domain-level rating (`domain.score`, one segment) counts as a rating of
    that domain like any other.
    """
    letters: dict[str, list[str]] = {}
    for path, value in field_values.items():
        parts = _score_path_parts(path)
        if parts is None or not isinstance(value, str):
            continue
        letters.setdefault(parts[0], []).append(value)

    out: dict[str, float] = {}
    for domain_id, ratings in letters.items():
        majority = majority_rag(ratings)
        if majority is not None:
            out[domain_id] = RAG_SCORES[majority]
    return out


def station_score(scores: Mapping[str, float]) -> float | None:
    """The station's score: the mean of its domains, equally weighted.

    A domain with twelve skills counts the same as one with two.
    """
    if not scores:
        return None
    return sum(scores.values()) / len(scores)


def apply_review_overrides(marked: Mapping[str, object], reviewed: Mapping[str, object]) -> dict[str, float]:
    """The scores after a GP lead has had their say.

    Two kinds of override: a **skill** rating (`domain.skill.score`) is laid
    over the marking and the domain's majority is recomputed, so one changed
    skill may not move the domain at all; a **domain** rating (`domain.score`)
    replaces the domain outright.
    """
    overlaid: dict[str, object] = dict(marked)
    domain_level: dict[str, str] = {}
    for path, value in reviewed.items():
        parts = _score_path_parts(path)
        if parts is None or not isinstance(value, str):
            continue
        if len(parts) == 1:
            domain_level[parts[0]] = value
        else:
            overlaid[path] = value

    effective = domain_scores(overlaid)
    for domain_id, rag in domain_level.items():
        try:
            effective[domain_id] = score_for(rag)
        except (InvalidRag, KeyError):
            continue
    return effective


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
