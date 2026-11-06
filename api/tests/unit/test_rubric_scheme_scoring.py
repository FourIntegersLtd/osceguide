"""A scheme marks exactly what its compiled form marks, and its new rules and scales score as written."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from app.features.rubrics import authoring, domain, scheme
from app.features.rubrics import service_scoring as scoring
from app.features.rubrics.structure import RubricStructure

_SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())


def _v2(code: str) -> dict[str, Any]:
    return next(entry["rubric"]["structure"] for entry in _SEED["exams"] if entry["code"] == code)


def _pair(raw: Mapping[str, Any]) -> tuple[RubricStructure, dict[str, Any]]:
    structure = domain.parse_structure(raw)
    return structure, domain.resolved_display(structure)


def _result(structure: RubricStructure, ratings: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    by_id = {section.id: section for section in structure.domains}
    result: dict[str, Any] = {}
    for domain_id, values in ratings.items():
        competencies = by_id[domain_id].competencies
        result[domain_id] = {
            competency.id: {structure.rating.field: value}
            for competency, value in zip(competencies, values, strict=False)
        }
    return result


@pytest.mark.parametrize(
    ("code", "ratings"),
    [
        ("sca", {"global_skills": ["G", "A"], "tasks": ["R"], "relating_to_others": ["G"]}),
        (
            "plab",
            {
                "data_gathering": [1, 1, 0.5, 0.5],
                "clinical_management": [1, 1, 1, 1],
                "interpersonal_skills": [0.5, 0.5, 0, 0],
            },
        ),
        ("casc", {"history": [True] * 6, "examination": [True, True, True, False]}),
        ("ortho", {"clinical_skills": [8, 8, 7, 7, 6]}),
    ],
)
def test_seed_totals_are_unchanged_through_the_scheme(code: str, ratings: dict[str, list[Any]]) -> None:
    old, old_display = _pair(_v2(code))
    new, new_display = _pair(scheme.upgrade_v2_to_v3(_v2(code)))
    result = _result(old, ratings)
    assert scoring.result_totals(old, old_display, result) == scoring.result_totals(new, new_display, result)


def test_three_of_four_at_amber_or_better_passes_a_domain() -> None:
    v3 = scheme.upgrade_v2_to_v3(_v2("sca"))
    domain_rule = {"type": "labels", "atLeast": 3, "of": "count", "value": "A"}
    v3["pass"]["domain"] = {"score": "labels", "rule": domain_rule}
    v3["pass"]["overall"] = {
        "score": "labels",
        "rule": {"type": "labels", "atLeast": 0, "of": "percent", "value": "G"},
        "everyDomainPasses": True,
    }
    compiled = scheme.compile_v3(v3)
    assert compiled["display"]["domain"] == {"aggregate": "ragCounts", "rule": domain_rule}
    assert compiled["display"]["total"] == {
        "aggregate": "ragShare",
        "passAtLeast": 0,
        "requireEveryDomain": True,
    }
    structure, display = _pair(v3)
    failing = _result(
        structure,
        {
            "global_skills": ["G", "A", "A", "R"],
            "tasks": ["G", "G", "A", "A"],
            "relating_to_others": ["A", "R", "R", "R"],
        },
    )
    totals = scoring.result_totals(structure, display, failing)
    assert [d.passed for d in totals.domains] == [True, True, False]
    assert totals.passed is False
    passing = _result(
        structure,
        {
            "global_skills": ["G", "A", "A", "R"],
            "tasks": ["G", "G", "A", "A"],
            "relating_to_others": ["A", "A", "A", "R"],
        },
    )
    totals = scoring.result_totals(structure, display, passing)
    assert [d.passed for d in totals.domains] == [True, True, True]
    assert totals.passed is True


def _three_competencies() -> dict[str, Any]:
    v3 = authoring.blank_scheme()
    v3["outline"][0]["competencies"] += [
        {"id": "competency_2", "label": "Competency 2", "instructions": ""},
        {"id": "competency_3", "label": "Competency 3", "instructions": ""},
    ]
    return v3


def test_the_clear_pass_preset_scores_three_two_one_nothing() -> None:
    v3 = _three_competencies()
    values = ("clear_pass", "pass", "fail", "clear_fail")
    v3["scales"] = [
        {
            "id": "clear_pass",
            "name": "Clear pass to clear fail",
            "levels": [
                {"value": value, "label": label, "points": points}
                for value, label, points in zip(
                    values, ("Clear pass", "Pass", "Fail", "Clear fail"), (3, 2, 1, 0), strict=True
                )
            ],
        }
    ]
    v3["outline"][0]["scale"] = "clear_pass"
    v3["pass"] = {
        "domain": {"score": "sum"},
        "overall": {"score": "sum", "rule": {"type": "score", "atLeast": 4}},
    }
    assert scheme.compile_v3(v3)["rating"] == {
        "kind": "scale",
        "field": "score",
        "scale": list(values),
        "points": [3, 2, 1, 0],
    }
    structure, display = _pair(v3)
    assert [scoring.rating_fraction(structure, v) for v in values] == [1.0, 0.66, 0.33, 0.0]
    good = scoring.result_totals(
        structure, display, _result(structure, {"domain_1": ["clear_pass", "pass", "fail"]})
    )
    assert good.total == 6.0
    assert good.maximum == 9
    assert good.passed is True
    poor = scoring.result_totals(
        structure, display, _result(structure, {"domain_1": ["fail", "fail", "clear_fail"]})
    )
    assert poor.total == 2.0
    assert poor.passed is False


def test_the_pass_fail_preset_is_a_yes_no_rating() -> None:
    v3 = _three_competencies()
    v3["scales"] = [
        {
            "id": "pass_fail",
            "name": "Pass / Fail",
            "levels": [
                {"value": True, "label": "Pass", "points": 1},
                {"value": False, "label": "Fail", "points": 0},
            ],
        }
    ]
    v3["outline"][0]["scale"] = "pass_fail"
    v3["pass"] = {
        "domain": {"score": "percent"},
        "overall": {"score": "percent", "rule": {"type": "score", "atLeast": 50}},
    }
    assert scheme.compile_v3(v3)["rating"] == {"kind": "boolean", "field": "score"}
    structure, display = _pair(v3)
    totals = scoring.result_totals(structure, display, _result(structure, {"domain_1": [True, False, True]}))
    assert totals.total == pytest.approx(200 / 3)
    assert totals.passed is True


def test_a_labels_rule_on_a_number_scale_counts_ratings_at_or_above_the_value() -> None:
    v3 = scheme.upgrade_v2_to_v3(_v2("plab"))
    v3["pass"]["domain"] = {
        "score": "sum",
        "rule": {"type": "labels", "atLeast": 3, "of": "count", "value": 0.5},
    }
    structure, display = _pair(v3)
    result = _result(structure, {"data_gathering": [1, 0.5, 0.5, 0], "clinical_management": [1, 1, 0, 0]})
    totals = scoring.result_totals(structure, display, result)
    assert [d.passed for d in totals.domains][:2] == [True, False]


def test_a_labels_scheme_that_sums_uses_points_and_an_old_one_keeps_fractions() -> None:
    blank_domain = authoring.blank_structure()["sections"][0]
    v2 = {
        "schemaVersion": 2,
        "rating": {"kind": "rag", "field": "score", "scale": ["G", "A", "R"]},
        "display": {"domain": {"aggregate": "sum"}, "total": {"aggregate": "sum"}},
        "sections": [blank_domain],
    }
    v3 = scheme.upgrade_v2_to_v3(v2)
    assert v3["advanced"]["legacyUnits"] is True
    assert "points" not in scheme.compile_v3(v3)["rating"]
    modern = copy.deepcopy(v3)
    modern["advanced"]["legacyUnits"] = False
    assert scheme.compile_v3(modern)["rating"]["points"] == [3, 2, 1]


def test_a_tied_top_does_not_compile_a_percent_at_best_into_a_pass_line() -> None:
    v3 = _three_competencies()
    v3["scales"] = [
        {
            "id": "rag",
            "levels": [
                {"value": "Excellent", "label": "Excellent", "points": 3},
                {"value": "Good", "label": "Good", "points": 3},
                {"value": "Poor", "label": "Poor", "points": 1},
            ],
        }
    ]
    v3["pass"] = {
        "domain": {
            "score": "labels",
            "rule": {"type": "labels", "atLeast": 50, "of": "percent", "value": "Excellent"},
        }
    }
    structure, display = _pair(v3)
    result = _result(structure, {"domain_1": ["Good", "Good", "Poor"]})
    totals = scoring.result_totals(structure, display, result)
    assert [entry.passed for entry in totals.domains] == [False]


def test_a_range_ignores_stray_points() -> None:
    raw = copy.deepcopy(_v2("ortho"))
    raw["rating"]["points"] = [1]
    structure = domain.parse_structure(raw)
    assert structure.rating.points is None
    assert structure.rating.maximum == 10


def test_tied_top_points_still_count_only_the_first_level_as_best() -> None:
    v3 = _three_competencies()
    v3["scales"][0]["levels"][1]["points"] = 3
    structure, display = _pair(v3)
    assert scoring.domain_value(structure, display, ["G", "A", "R"]) == pytest.approx(100 / 3)


def test_a_best_level_worth_zero_points_is_refused() -> None:
    v3 = _three_competencies()
    for level in v3["scales"][0]["levels"]:
        level["points"] = 0
    assert scheme.validate_scheme(v3) != []
