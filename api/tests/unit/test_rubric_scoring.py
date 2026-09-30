"""What one marked result adds up to, for each seeded exam, read from its rubric alone.

Every number here is written out by hand from the rubric's display (plan
§4): the aggregate, the maximum and the pass line are data, and nothing in
`rubrics.scoring` names an exam.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from app.features.rubrics import domain as rubric_domain
from app.features.rubrics import service_scoring as scoring
from app.features.rubrics.structure import RubricStructure

_SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())


def _seeded(exam_code: str) -> tuple[RubricStructure, dict[str, Any]]:
    """A seeded exam's parsed structure and resolved display."""
    raw = next(entry["rubric"]["structure"] for entry in _SEED["exams"] if entry["code"] == exam_code)
    structure = rubric_domain.parse_structure(raw)
    return structure, rubric_domain.resolved_display(structure)


def _result(structure: RubricStructure, ratings: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    """A result rating each domain's first competencies, in order, with the given values."""
    by_id = {section.id: section for section in structure.domains}
    result: dict[str, Any] = {}
    for domain_id, values in ratings.items():
        competencies = by_id[domain_id].competencies
        result[domain_id] = {
            competency.id: {structure.rating.field: value}
            for competency, value in zip(competencies, values, strict=False)
        }
    return result


def test_sca_totals_the_share_of_greens_and_sets_no_pass_line() -> None:
    structure, display = _seeded("sca")
    result = _result(structure, {"global_skills": ["G", "A"], "tasks": ["R"], "relating_to_others": ["G"]})
    result["clinical_analysis"] = {"safety_considerations": ["Did not ask about haemoptysis"]}
    totals = scoring.result_totals(structure, display, result)
    assert totals.total == 50.0
    assert totals.passed is None
    # One red rating and one flagged safety consideration.
    assert totals.critical_count == 2
    assert totals.domains[0].counts == {"G": 1, "A": 1, "R": 0}


def test_plab_passes_on_the_total_only_when_every_domain_clears_its_own_line() -> None:
    structure, display = _seeded("plab")
    weak_domain = _result(
        structure,
        {
            "data_gathering": [1, 1, 0.5, 0.5],
            "clinical_management": [1, 1, 1, 1],
            "interpersonal_skills": [0.5, 0.5, 0, 0],
        },
    )
    totals = scoring.result_totals(structure, display, weak_domain)
    assert (totals.total, totals.maximum) == (8.0, 12.0)
    # 8 clears the 7 but interpersonal skills scored 1 of a required 2.
    assert totals.passed is False
    assert [domain.passed for domain in totals.domains] == [True, True, False]
    # The ratings under 0.6 of the maximum are the poor ones: 0.5, 0.5, 0.5, 0.5, 0, 0.
    assert totals.critical_count == 6

    every_domain_clears = _result(
        structure,
        {
            "data_gathering": [1, 1, 0.5, 0.5],
            "clinical_management": [1, 1, 1, 1],
            "interpersonal_skills": [1, 0.5, 0.5, 0],
        },
    )
    assert scoring.result_totals(structure, display, every_domain_clears).total == 9.0
    assert scoring.result_totals(structure, display, every_domain_clears).passed is True


def test_casc_is_the_share_of_competencies_met() -> None:
    structure, display = _seeded("casc")
    result = _result(structure, {"history": [True] * 6, "examination": [True, True, True, False]})
    totals = scoring.result_totals(structure, display, result)
    assert totals.total == 90.0
    assert totals.passed is True
    assert [domain.value for domain in totals.domains] == [100.0, 75.0]
    assert totals.critical_count == 1


def test_ortho_sums_the_one_domain_the_station_answered() -> None:
    structure, display = _seeded("ortho")
    result = _result(structure, {"clinical_skills": [8, 8, 7, 7, 6]})
    result["communication_skills"] = None
    totals = scoring.result_totals(structure, display, result)
    assert (totals.total, totals.maximum, totals.fraction) == (36.0, 50, 0.72)
    assert totals.passed is True
    assert [(domain.id, domain.value) for domain in totals.domains] == [("clinical_skills", 7.2)]
    assert totals.critical_count == 0


@pytest.mark.parametrize(
    ("exam_code", "values", "worst"),
    [
        ("sca", ["G", "R", "A"], "R"),
        ("ortho", [7, 5, 9], 5),
        ("casc", [True, False], False),
        ("casc", [True, True], True),
        ("sca", ["not a rating", None], None),
    ],
)
def test_the_worst_rating_is_the_one_a_reader_must_see(exam_code: str, values: list[Any], worst: Any) -> None:
    structure, _ = _seeded(exam_code)
    assert scoring.worst_rating(structure, values) == worst


def test_reviewers_on_a_range_are_averaged_and_on_a_boolean_a_tie_is_not_met() -> None:
    ortho, _ = _seeded("ortho")
    casc, _ = _seeded("casc")
    assert scoring.combine_reviewers(ortho, [6, 9]) == 7.5
    assert scoring.combine_reviewers(casc, [True, False]) is False
    assert scoring.combine_reviewers(casc, [True, True, False]) is True


@pytest.mark.parametrize(
    ("fraction", "tone"), [(0.95, "excellent"), (0.72, "good"), (0.4, "fair"), (0.1, "poor"), (None, None)]
)
def test_a_fraction_falls_in_the_display_s_tone(fraction: float | None, tone: str | None) -> None:
    _, display = _seeded("ortho")
    assert scoring.tone_for_fraction(display, fraction) == tone
