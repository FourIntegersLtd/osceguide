"""A rubric is data, and the schema a marker fills is derived from it.

The derivation is the load-bearing part: the descriptors an author types are
the descriptors the model reads. They used to be two files kept in step by
hand — a Python constant naming the competencies and a JSON Schema whose
`description` strings held the marking anchors — which is exactly the drift
this removes.
"""

from __future__ import annotations

import pytest

from app.features.rubrics import domain
from tests.support.rubrics import FULL_RUBRIC, MINIMAL_RUBRIC, PACING


def test_a_rubric_becomes_the_schema_its_own_competencies_describe() -> None:
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))

    assert schema["required"] == ["global_skills", "tasks", "actionable_feedback", "clinical_analysis"]
    assert schema["additionalProperties"] is False
    scored = schema["properties"]["global_skills"]["properties"]["structures_consultation"]
    assert scored["required"] == ["score", "supporting_phrase", "score_explanation"]
    assert scored["properties"]["score"]["enum"] == ["R", "A", "G"]


def test_the_descriptors_the_author_typed_are_what_the_model_reads() -> None:
    """The whole point. These lived only in a hand-written schema's description strings."""
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))
    described = schema["properties"]["global_skills"]["properties"]["structures_consultation"]["description"]

    assert "Clear opening, systematic history" in described
    assert "R: Misses several" in described
    # In scale order, not dict order, so R/A/G reads the way the rubric is written.
    assert described.index("R:") < described.index("A:") < described.index("G:")


def test_a_competency_with_no_descriptors_still_scores() -> None:
    """An author may name a competency without spelling out its anchors."""
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))
    bare = schema["properties"]["global_skills"]["properties"]["avoids_repetition"]

    assert bare["description"] == "Avoids repetition"
    assert bare["properties"]["score"]["enum"] == ["R", "A", "G"]


def test_a_scale_is_whatever_the_author_chose() -> None:
    """RAG was hard-coded in the engine. A four-point rubric was unrepresentable."""
    structure = domain.parse_structure(
        {
            "scale": ["fail", "borderline", "pass", "distinction"],
            "domains": [
                {
                    "id": "d",
                    "label": "D",
                    "competencies": [{"id": "c", "label": "C", "descriptors": {"pass": "Enough."}}],
                }
            ],
        }
    )
    schema = domain.derive_result_schema(structure)

    assert schema["properties"]["d"]["properties"]["c"]["properties"]["score"]["enum"] == [
        "fail",
        "borderline",
        "pass",
        "distinction",
    ]


def test_sections_take_the_shape_their_author_chose() -> None:
    schema = domain.derive_result_schema(domain.parse_structure(FULL_RUBRIC))

    assert schema["properties"]["actionable_feedback"] == {
        "type": "array",
        "title": "Actionable feedback",
        "items": {"type": "string"},
    }
    assert schema["properties"]["clinical_analysis"]["required"] == ["missed_history"]


@pytest.mark.parametrize(
    ("broken", "because"),
    [
        ({"scale": [], "domains": []}, "a rubric with no scale cannot score anything"),
        ({"scale": ["R", "R"], "domains": []}, "a repeated score is two names for one thing"),
        ({"scale": ["R"], "domains": [], "sections": []}, "it asks the marker for nothing"),
        (
            {"scale": ["R"], "domains": [{"id": "Bad Id", "label": "x", "competencies": []}]},
            "an id becomes a JSON property name",
        ),
        (
            {
                "scale": ["R"],
                "domains": [
                    {"id": "a", "label": "A", "competencies": [{"id": "c", "label": "C"}]},
                    {"id": "b", "label": "B", "competencies": [{"id": "c", "label": "C"}]},
                ],
            },
            "a duplicate competency id silently drops one from the result",
        ),
        (
            {"scale": ["R", "A"], "domains": [], "sections": [{"id": "s", "label": "S", "kind": "object"}]},
            "an object section with no schema describes nothing",
        ),
    ],
)
def test_a_rubric_that_could_not_be_marked_against_is_refused(broken: dict, because: str) -> None:
    with pytest.raises(domain.InvalidRubric):
        domain.parse_structure(broken)


def test_a_descriptor_for_a_score_off_the_scale_is_refused() -> None:
    """It would be an instruction the model cannot follow."""
    with pytest.raises(domain.InvalidRubric, match="not on the scale"):
        domain.parse_structure(
            {
                "scale": ["R", "A", "G"],
                "domains": [
                    {
                        "id": "d",
                        "label": "D",
                        "competencies": [{"id": "c", "label": "C", "descriptors": {"EXCELLENT": "..."}}],
                    }
                ],
            }
        )


def test_the_override_replaces_the_derivation_entirely() -> None:
    """The escape hatch, for a shape the derivation cannot express."""
    structure = domain.parse_structure(MINIMAL_RUBRIC)
    override = {"type": "object", "properties": {"anything": {"type": "string"}}}

    assert domain.result_schema_for(structure, override) == override
    assert domain.result_schema_for(structure, None) == domain.derive_result_schema(structure)


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
    assert framework.competency_ids == ("structures_consultation", "avoids_repetition", "discovers_ice")
    assert framework.competencies[0].descriptors["A"] == "Misses one element."
    assert framework.system_prompt == "Mark it."


@pytest.mark.parametrize(
    "broken",
    [
        {"total_seconds": 0, "history_seconds": 1, "introduction_seconds": 1, "safety_net_seconds": 1},
        {"total_seconds": 600, "history_seconds": 30, "introduction_seconds": 60, "safety_net_seconds": 100},
        {"total_seconds": 600, "history_seconds": 550, "introduction_seconds": 30, "safety_net_seconds": 100},
        {"total_seconds": 600, "history_seconds": 300},
    ],
)
def test_a_clock_that_cannot_be_run_is_refused_when_it_is_written(broken: dict) -> None:
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

    assert [d.id for d in narrowed.domains] == ["tasks"]
    assert [s.id for s in narrowed.sections] == ["actionable_feedback", "clinical_analysis"]


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
