"""A rubric is data, and the schema a marker fills is derived from it.

The derivation is the load-bearing part: the instructions an author types are
the instructions the model reads. Stored structures come in two versions;
version 1 is upgraded on every read, so these tests use both: the test support
rubrics (`tests/support/rubrics.py`) are version 1, the way org rubrics and
frozen attempts are stored today, and the seeded platform rubrics are
version 2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.features.rubrics import domain, validation
from tests.support.rubrics import FULL_RUBRIC, PACING

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
V1_SEED: dict[str, Any] = json.loads((FIXTURES / "rubrics_v1/platform-starter-v1.json").read_text())
SEED = json.loads((Path(__file__).resolve().parents[2] / "seeds/platform-starter.json").read_text())
SEEDED = {entry["code"]: entry["rubric"]["structure"] for entry in SEED["exams"]}
EXAM_CODES = ("sca", "plab", "casc", "ortho")


def _domain_v2(rating_field: str = "score", **overrides: Any) -> dict[str, Any]:
    """A one-competency version 2 domain, for a rubric built in a test."""
    return {
        "kind": "domain",
        "id": "consulting",
        "title": "Consulting",
        "competencies": [{"id": "opens", "label": "Opens"}, {"id": "closes", "label": "Closes"}],
        "competencyFields": [{"id": rating_field, "type": "rating", "role": "rating"}],
        **overrides,
    }


def _rubric_v2(rating: dict[str, Any], *sections: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """A version 2 structure with this rating and these sections."""
    return {"schemaVersion": 2, "rating": rating, "sections": list(sections) or [_domain_v2()], **extra}


# --- Version 1 rubrics, upgraded on read -------------------------------------------


def test_a_version_1_rubric_derives_the_shape_it_always_had() -> None:
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))

    assert schema["required"] == ["global_skills", "tasks", "actionable_feedback", "clinical_analysis"]
    assert schema["additionalProperties"] is False
    scored = schema["properties"]["global_skills"]["properties"]["structures_consultation"]
    assert scored["required"] == ["score", "supporting_phrase", "score_explanation"]
    # R/A/G is written best first in version 2; the values are unchanged.
    assert scored["properties"]["score"] == {"type": "string", "enum": ["G", "A", "R"]}
    assert scored["properties"]["supporting_phrase"] == {"type": "string"}


def test_the_descriptors_the_author_typed_are_what_the_model_reads() -> None:
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))
    described = schema["properties"]["global_skills"]["properties"]["structures_consultation"]["description"]

    assert described == (
        "Structures the consultation\n"
        "G: Clear opening, systematic history, signposted throughout.\n"
        "A: Misses one element.\n"
        "R: Misses several, or the consultation has no shape."
    )


def test_a_competency_with_no_descriptors_is_described_by_its_label() -> None:
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))
    bare = schema["properties"]["global_skills"]["properties"]["avoids_repetition"]

    assert bare["description"] == "Avoids repetition"
    assert bare["properties"]["score"]["enum"] == ["G", "A", "R"]


def test_version_1_guidance_becomes_instructions_read_after_the_anchors() -> None:
    upgraded = domain.upgrade_structure(
        {
            "scale": ["R", "A", "G"],
            "domains": [
                {
                    "id": "data_gathering",
                    "label": "Data gathering",
                    "guidance": "Clinical information gathering.",
                    "competencies": [
                        {
                            "id": "history_taking",
                            "label": "History taking",
                            "descriptors": {"G": "Systematic and complete."},
                            "guidance": "Assessment of:\n- Red flag symptoms",
                        }
                    ],
                }
            ],
        }
    )
    schema = domain.derive_result_schema(domain.parse_structure(upgraded))
    gathering = schema["properties"]["data_gathering"]

    assert upgraded["sections"][0]["instructions"] == "Clinical information gathering."
    assert gathering["description"] == "Clinical information gathering."
    assert gathering["properties"]["history_taking"]["description"] == (
        "G: Systematic and complete.\nAssessment of:\n- Red flag symptoms"
    )


def test_a_version_1_scale_that_is_not_rag_stays_a_scale_in_its_own_order() -> None:
    upgraded = domain.upgrade_structure(
        {
            "scale": ["fail", "borderline", "pass", "distinction"],
            "domains": [{"id": "d", "label": "D", "competencies": [{"id": "c", "label": "C"}]}],
        }
    )

    assert upgraded["rating"] == {
        "kind": "scale",
        "field": "score",
        "scale": ["fail", "borderline", "pass", "distinction"],
    }


def test_version_1_sections_become_lone_fields() -> None:
    upgraded = domain.upgrade_structure(FULL_RUBRIC)

    assert upgraded["sections"][2:] == [
        {
            "kind": "field",
            "field": {
                "id": "actionable_feedback",
                "label": "Actionable feedback",
                "type": "list",
                "role": "summary",
            },
        },
        {
            "kind": "field",
            "field": {
                "id": "clinical_analysis",
                "label": "Clinical analysis",
                "type": "group",
                "required": True,
                "role": "other",
                "fields": [
                    {
                        "id": "missed_history",
                        "label": "Missed history",
                        "type": "list",
                        "required": True,
                        "role": "improvement",
                    }
                ],
            },
        },
    ]
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))
    assert schema["properties"]["actionable_feedback"] == {
        "type": "array",
        "items": {"type": "string"},
        "title": "Actionable feedback",
    }
    assert schema["properties"]["clinical_analysis"]["required"] == ["missed_history"]


@pytest.mark.parametrize("code", EXAM_CODES)
def test_every_version_1_platform_rubric_upgrades_and_keeps_its_ids(code: str) -> None:
    """The structures stored before version 2, verbatim: each must still be markable."""
    stored = V1_SEED[code]

    upgraded = domain.upgrade_structure(stored)
    structure = domain.parse_structure(stored)

    assert validation.validate_structure(upgraded) == []
    assert [(section.id, [c.id for c in section.competencies]) for section in structure.domains] == [
        (raw["id"], [competency["id"] for competency in raw["competencies"]]) for raw in stored["domains"]
    ]
    assert [section.id for section in structure.sections if section.kind == "field"] == [
        raw["id"] for raw in stored["sections"]
    ]


def test_a_version_2_structure_is_read_as_it_is() -> None:
    assert domain.upgrade_structure(SEEDED["plab"]) == SEEDED["plab"]


# --- Refusals ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("broken", "message"),
    [
        ({"scale": [], "domains": []}, "A rubric needs a scale: the scores a competency may be given."),
        (
            {
                "scale": ["R", "R"],
                "domains": [{"id": "d", "label": "D", "competencies": [{"id": "c", "label": "C"}]}],
            },
            "The scale repeats a value; each must appear once. (at rating.scale)",
        ),
        (
            {"scale": ["R"], "domains": [], "sections": []},
            "A rubric needs at least one section: it would ask the marker for nothing. (at sections)",
        ),
        (
            {
                "scale": ["R", "A", "G"],
                "domains": [],
                "sections": [{"id": "s", "label": "S", "kind": "object"}],
            },
            "Section 's' is an object and needs a schema describing it.",
        ),
    ],
)
def test_a_rubric_that_could_not_be_marked_against_is_refused(broken: dict[str, Any], message: str) -> None:
    with pytest.raises(domain.InvalidRubric) as refused:
        domain.parse_structure(broken)

    assert str(refused.value) == message


def test_a_refusal_carries_every_problem_not_just_the_first() -> None:
    broken = {
        "scale": ["R", "A", "G"],
        "domains": [
            {
                "id": "Bad Id",
                "label": "x",
                "competencies": [{"id": "c", "label": "C", "descriptors": {"EXCELLENT": "..."}}],
            }
        ],
    }
    with pytest.raises(domain.InvalidRubric) as refused:
        domain.parse_structure(broken)

    assert domain.validation_errors(refused.value) == [
        {"path": "sections[0].id", "message": validation.IDENTIFIER_MESSAGE},
        {
            "path": "sections[0].competencies[0].descriptors.EXCELLENT",
            "message": "'EXCELLENT' is not on the rating scale (G, A, R).",
        },
    ]
    assert str(refused.value).endswith("1 more problem(s) listed.")


# --- The engine contract ------------------------------------------------------------


def test_the_framework_payload_is_what_the_engine_validates() -> None:
    """Built as a dict here so this slice never imports the engine; the engine checks it."""
    from osce_assessment.contracts import CompetencyFramework

    payload = domain.framework_payload(
        framework_id="11111111-1111-1111-1111-111111111111",
        label="Marking rubric",
        version="3",
        structure=domain.parse_structure(FULL_RUBRIC),
        system_prompt="Mark it.",
    )
    framework = CompetencyFramework.model_validate(payload)

    assert framework.live_domain_ids == ("tasks",)
    # Each competency keeps its own id: the live coverage panel keys on it.
    assert framework.competency_ids == ("structures_consultation", "avoids_repetition", "discovers_ice")
    assert framework.competencies[0].descriptors["A"] == "Misses one element."
    assert framework.system_prompt == "Mark it."


def test_only_a_competency_name_two_domains_share_is_qualified() -> None:
    """Ortho repeats competency names across its domains; the framework needs ids unique."""
    payload = domain.framework_payload(
        framework_id="11111111-1111-1111-1111-111111111111",
        label="Ortho",
        version="1",
        structure=domain.parse_structure(SEEDED["ortho"]),
        system_prompt="Mark it.",
    )
    ids = [competency["id"] for competency in payload["competencies"]]

    assert len(ids) == len(set(ids)) == 20
    assert "situational_awareness" not in ids
    assert sum(competency_id.endswith(".situational_awareness") for competency_id in ids) == 3
    assert sum("." not in competency_id for competency_id in ids) == 5


# What each seeded rubric tells the engine about its rating: (rating, rating field,
# nullable domains, one field the tutor must read by role and that role).
SEEDED_FRAMEWORK_FACTS = {
    "sca": (
        {"kind": "rag", "minimum": None, "maximum": None, "step": "number"},
        "score",
        0,
        ("supporting_phrase", "evidence"),
    ),
    "plab": (
        {"kind": "range", "minimum": 0, "maximum": 1, "step": "number"},
        "score",
        0,
        ("critical_flags", "flag"),
    ),
    "casc": (
        {"kind": "boolean", "minimum": None, "maximum": None, "step": "number"},
        "competent",
        0,
        ("competent", "rating"),
    ),
    "ortho": (
        {"kind": "range", "minimum": 0, "maximum": 10, "step": "integer"},
        "score",
        4,
        ("station_type", "selector"),
    ),
}


@pytest.mark.parametrize("code", EXAM_CODES)
def test_every_seeded_rubric_is_a_framework_the_engine_accepts(code: str) -> None:
    """The engine gets each exam's native rating, its nullable domains and every field's role."""
    from osce_assessment.contracts import CompetencyFramework

    payload = domain.framework_payload(
        framework_id="11111111-1111-1111-1111-111111111111",
        label=code,
        version="1",
        structure=domain.parse_structure(SEEDED[code]),
        system_prompt="Mark it.",
    )
    framework = CompetencyFramework.model_validate(payload)
    rating, rating_field, nullable_count, (field_id, role) = SEEDED_FRAMEWORK_FACTS[code]

    assert framework.result_schema == payload["result_schema"]
    assert framework.rating.model_dump() == rating
    assert framework.rating_field == rating_field
    assert sum(1 for framework_domain in framework.domains if framework_domain.nullable) == nullable_count
    assert framework.role_of(field_id) == role


# --- Display defaults (plan §4.2) and the seeded values (§4.3) ------------------------


def test_a_rag_rubric_reads_as_counts_and_a_share_with_tones_by_position() -> None:
    display = domain.resolved_display(domain.parse_structure(_rubric_v2({"kind": "rag"})))

    assert display == {
        "domain": {"aggregate": "ragCounts", "max": None, "passAtLeast": None},
        "total": {"aggregate": "ragShare", "max": None, "passAtLeast": None, "requireEveryDomain": False},
        "tones": [
            {"value": "G", "atLeast": 1, "tone": "good"},
            {"value": "A", "atLeast": 0.5, "tone": "fair"},
            {"value": "R", "atLeast": 0, "tone": "poor"},
        ],
        "bands": [],
        "labels": {},
        "show": {"overall": True, "areaScores": True, "wentWell": True, "workOn": True, "quotes": True},
        "feedbackTone": None,
    }


def test_a_scale_rubric_takes_its_tones_from_each_values_place() -> None:
    rating = {"kind": "scale", "scale": ["distinction", "pass", "borderline", "fail"]}

    display = domain.resolved_display(domain.parse_structure(_rubric_v2(rating)))

    assert display["domain"]["aggregate"] == "ragCounts"
    assert display["tones"] == [
        {"value": "distinction", "atLeast": 1, "tone": "good"},
        {"value": "pass", "atLeast": 0.6667, "tone": "fair"},
        {"value": "borderline", "atLeast": 0.3333, "tone": "fair"},
        {"value": "fail", "atLeast": 0, "tone": "poor"},
    ]


def test_a_range_rubric_sums_to_the_rating_maximum_times_its_competencies() -> None:
    rating = {"kind": "range", "minimum": 0, "maximum": 5, "step": "integer"}

    display = domain.resolved_display(domain.parse_structure(_rubric_v2(rating)))

    assert display["domain"] == {"aggregate": "sum", "max": 10, "passAtLeast": None}
    assert display["total"] == {
        "aggregate": "sum",
        "max": 10,
        "passAtLeast": None,
        "requireEveryDomain": False,
    }
    assert display["tones"] == [
        {"atLeast": 0.8, "tone": "good"},
        {"atLeast": 0.6, "tone": "fair"},
        {"atLeast": 0, "tone": "poor"},
    ]


def test_a_boolean_rubric_reads_as_the_percentage_achieved() -> None:
    display = domain.resolved_display(
        domain.parse_structure(_rubric_v2({"kind": "boolean", "field": "competent"}, _domain_v2("competent")))
    )

    assert display["domain"] == {"aggregate": "percentAchieved", "max": 100, "passAtLeast": None}
    assert display["total"]["max"] == 100


def test_ortho_is_out_of_fifty_because_only_one_station_domain_is_filled() -> None:
    """Five competencies in the one always-marked domain, and five in whichever nullable station applies."""
    display = domain.resolved_display(domain.parse_structure(SEEDED["ortho"]))

    assert display["total"] == {"aggregate": "sum", "max": 50, "passAtLeast": 35, "requireEveryDomain": False}
    assert display["domain"] == {"aggregate": "mean", "max": 10, "passAtLeast": 7}
    assert [band["to"] for band in display["bands"]] == [17, 34, 42, 50]


def test_plab_passes_on_twelve_and_every_domain() -> None:
    display = domain.resolved_display(domain.parse_structure(SEEDED["plab"]))

    assert display["domain"] == {"aggregate": "sum", "max": 4, "passAtLeast": 2}
    assert display["total"] == {"aggregate": "sum", "max": 12, "passAtLeast": 7, "requireEveryDomain": True}
    assert display["labels"]["passLabel"] == "Pass (7/12)"


def test_casc_passes_on_eighty_percent_overall_only() -> None:
    display = domain.resolved_display(domain.parse_structure(SEEDED["casc"]))

    assert display["total"] == {
        "aggregate": "percentAchieved",
        "max": 100,
        "passAtLeast": 80,
        "requireEveryDomain": False,
    }


def test_sca_has_no_pass_line_and_no_dashboard_title() -> None:
    display = domain.resolved_display(domain.parse_structure(SEEDED["sca"]))

    assert display["total"] == {
        "aggregate": "ragShare",
        "max": None,
        "passAtLeast": None,
        "requireEveryDomain": False,
    }
    assert display["labels"] == {
        "domainSubtitle": "RAG mix by clinical domain",
        "trendSubtitle": "How your skills moved across recent sessions",
    }


def test_a_pass_line_above_the_derived_maximum_is_refused() -> None:
    """Two competencies rated 0 to 10 make 20 at most, which the author never typed."""
    ranged = {"kind": "range", "field": "score", "minimum": 0, "maximum": 10, "step": "integer"}

    with pytest.raises(domain.InvalidRubric) as refused:
        domain.parse_structure(_rubric_v2(ranged, display={"total": {"passAtLeast": 21}}))

    assert domain.validation_errors(refused.value) == [
        {
            "path": "display.total.passAtLeast",
            "message": "The pass line (21) is more than a candidate can score (20).",
        }
    ]


# --- Pacing and narrowing ---------------------------------------------------------


@pytest.mark.parametrize(
    "broken",
    [
        {"total_seconds": 0, "history_seconds": 1, "introduction_seconds": 1, "safety_net_seconds": 1},
        {"total_seconds": 600, "history_seconds": 30, "introduction_seconds": 60, "safety_net_seconds": 100},
        {"total_seconds": 600, "history_seconds": 550, "introduction_seconds": 30, "safety_net_seconds": 100},
        {"total_seconds": 600, "history_seconds": 300},
    ],
)
def test_a_clock_that_cannot_be_run_is_refused_when_it_is_written(broken: dict[str, Any]) -> None:
    """The author hears about it now, not when a candidate starts the station."""
    with pytest.raises(domain.InvalidRubric):
        domain.validate_pacing(broken)


def test_a_usable_clock_survives() -> None:
    assert domain.validate_pacing(PACING) == PACING


def test_narrowing_keeps_the_sections_the_candidate_reads() -> None:
    """A reviewer is not asked to agree with the narrative, but it is still shown."""
    narrowed = domain.narrow_structure(
        domain.parse_structure(FULL_RUBRIC), {"domains": ["tasks", "actionable_feedback"]}
    )

    assert [section.id for section in narrowed.domains] == ["tasks"]
    assert [section.id for section in narrowed.sections] == [
        "tasks",
        "actionable_feedback",
        "clinical_analysis",
    ]


def test_an_empty_selection_means_the_whole_rubric() -> None:
    structure = domain.parse_structure(FULL_RUBRIC)

    assert domain.narrow_structure(structure, None) == structure
    assert domain.narrow_structure(structure, {}) == structure


def test_a_selection_naming_a_domain_the_rubric_does_not_have_is_refused() -> None:
    with pytest.raises(domain.InvalidRubric, match="does not define"):
        domain.narrow_structure(domain.parse_structure(FULL_RUBRIC), {"domains": ["invented"]})


def test_a_path_selection_reads_the_same_as_a_domain_selection() -> None:
    """Both forms exist so a legacy import and an authored selection agree."""
    structure = domain.parse_structure(FULL_RUBRIC)

    by_path = domain.narrow_structure(structure, {"paths": ["tasks.discovers_ice"]})
    by_domain = domain.narrow_structure(structure, {"domains": ["tasks"]})

    assert by_path == by_domain


def test_a_generated_label_keeps_clinical_acronyms_in_capitals() -> None:
    """`discovers_ice` read "Discovers ice" on the live-marking cards (staging, 2026-10-03)."""
    from app.features.rubrics.legacy_model import humanise

    assert humanise("discovers_ice") == "Discovers ICE"
    assert humanise("person_specifications_cv_articulation") == "Person specifications CV articulation"
    assert humanise("ice_explored") == "ICE explored"
    assert humanise("explores_symptoms") == "Explores symptoms"
