"""Reading the marking engine's document into per-domain scores.

Fixtures are the real rubric structures from `seeds/platform-starter.json` and
payloads shaped like the frameworks in `tests/fixtures/legacy_schemas/b2c`, so
a change to either is caught here rather than by an empty chart.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.features.dashboard import performance

SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds" / "platform-starter.json").read_text())
STRUCTURES = {e["code"]: e["rubric"]["structure"] for e in SEED["exams"]}


def test_only_the_rubrics_own_domains_are_read() -> None:
    """A payload carries prose blocks as well as marks.

    `clinical_analysis` and `actionable_feedback` are narrative; counting them
    as domains would drag every score towards the same number and invent a
    domain nobody is marked on.
    """
    payload = {
        "global_skills": {"avoids_repetition": {"score": "G"}},
        "clinical_analysis": {"key_positives": ["not a score"]},
        "actionable_feedback": {"overall_priorities": ["also not a score"]},
    }
    assert set(performance.ratings_by_domain(payload, STRUCTURES["sca"])) == {"global_skills"}


def test_a_domain_scores_on_the_majority_of_its_competencies() -> None:
    # The institution rule, deliberately shared: three greens and a red is a
    # green domain with a red competency in it, not an amber that describes
    # neither.
    payload = {
        "global_skills": {
            "a": {"score": "G"},
            "b": {"score": "G"},
            "c": {"score": "G"},
            "d": {"score": "R"},
        }
    }
    assert performance.domain_scores(payload, STRUCTURES["sca"]) == {"global_skills": 100.0}


def test_a_split_domain_reports_the_lower_rating() -> None:
    # Worst first on a tie: the lower reading is the one worth a conversation.
    payload = {"global_skills": {"a": {"score": "G"}, "b": {"score": "R"}}}
    assert performance.domain_scores(payload, STRUCTURES["sca"]) == {"global_skills": 33.0}


def test_competency_ids_are_never_matched_by_name() -> None:
    """Ortho prefixes its competency ids with the domain; PLAB does not.

    Reading whatever is inside the domain block works for both, and avoids a
    table mapping one spelling to the other — which would be one more thing to
    keep in step with the seed.
    """
    ortho = {
        "clinical_skills": {
            "situational_awareness": {"score": "A"},
            "technical_knowledge_clinical_expertise": {"score": "A"},
        }
    }
    assert performance.domain_scores(ortho, STRUCTURES["ortho"]) == {"clinical_skills": 66.0}


def test_an_attempt_scores_the_mean_of_its_domains() -> None:
    # Equal weighting: a domain with twelve competencies counts the same as one
    # with four, which is the institution rule stated out loud.
    scores = {"a": 100.0, "b": 33.0}
    assert performance.attempt_score(scores) == pytest.approx(66.5)
    assert performance.attempt_score({}) is None


def test_reds_are_counted_across_every_domain() -> None:
    payload = {
        "global_skills": {"a": {"score": "R"}, "b": {"score": "G"}},
        "tasks": {"c": {"score": "R"}},
    }
    assert performance.critical_count(payload, STRUCTURES["sca"]) == 2


def test_a_rating_outside_the_vocabulary_leaves_the_domain_unscored() -> None:
    """A migration artefact must not be a 500 or a guess."""
    payload = {"global_skills": {"a": {"score": "excellent"}, "b": {"score": "7"}}}
    assert performance.domain_scores(payload, STRUCTURES["sca"]) == {}


def test_nothing_at_all_is_answered_with_nothing() -> None:
    assert performance.domain_scores(None, STRUCTURES["sca"]) == {}
    assert performance.domain_scores({}, None) == {}
    assert performance.scored_domain_ids(None) == []


@pytest.mark.parametrize("code", sorted(STRUCTURES))
def test_every_seeded_exam_names_its_domains_and_labels_them(code: str) -> None:
    ids = performance.scored_domain_ids(STRUCTURES[code])
    assert ids, f"{code} has no scored domains"
    labels = performance.domain_labels(STRUCTURES[code])
    assert set(labels) == set(ids)
    assert all(labels[i] for i in ids), f"{code} has an unlabelled domain"
