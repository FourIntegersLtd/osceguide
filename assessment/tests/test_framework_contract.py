"""A framework owns the shape of a result; a policy owns how it is scored."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from osce_assessment.contracts import (
    RAG_SCALE,
    Competency,
    CompetencyDomain,
    CompetencyFramework,
    InvalidScoreError,
    Rating,
    UnknownCompetencyError,
)

DOMAIN = CompetencyDomain(id="global_skills", label="Global skills")
OTHER_DOMAIN = CompetencyDomain(id="tasks", label="Tasks")
STRUCTURE = Competency(
    id="structures_consultation", label="Structures the consultation", domain_id=DOMAIN.id
)
LANGUAGE = Competency(
    id="uses_clear_language", label="Uses clear language", domain_id=DOMAIN.id
)
OPENING = Competency(
    id="opens_consultation", label="Opens the consultation", domain_id=OTHER_DOMAIN.id
)


def framework(**overrides: object) -> CompetencyFramework:
    base: dict[str, object] = {
        "id": "test-framework-v1",
        "label": "Test framework",
        "domains": (DOMAIN, OTHER_DOMAIN),
        "competencies": (STRUCTURE, LANGUAGE, OPENING),
    }
    base.update(overrides)
    return CompetencyFramework(**base)  # type: ignore[arg-type]


def test_shape_is_data_and_round_trips_as_json() -> None:
    """Shape must survive serialisation so it can come from a row, not only code."""
    original = framework()
    restored = CompetencyFramework.model_validate_json(original.model_dump_json())
    assert restored == original


def test_scale_defaults_to_the_platform_rag_convention() -> None:
    assert framework().scale == RAG_SCALE == ("R", "A", "G")


def test_domains_and_competencies_are_queryable() -> None:
    fw = framework()
    assert fw.domain_ids == ("global_skills", "tasks")
    assert fw.competency_ids == (
        "structures_consultation",
        "uses_clear_language",
        "opens_consultation",
    )
    assert fw.competencies_in("global_skills") == (STRUCTURE, LANGUAGE)
    assert fw.competencies_in("tasks") == (OPENING,)
    assert fw.competencies_in("nonexistent") == ()


def test_framework_is_immutable() -> None:
    with pytest.raises(ValidationError):
        framework().label = "renamed"  # type: ignore[misc]


def test_a_competency_cannot_sit_in_an_undeclared_domain() -> None:
    with pytest.raises(ValidationError, match="undeclared domains"):
        framework(domains=(DOMAIN,))


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate competency ids"):
        framework(competencies=(STRUCTURE, STRUCTURE))
    with pytest.raises(ValidationError, match="duplicate domain ids"):
        framework(domains=(DOMAIN, DOMAIN), competencies=())


def test_an_empty_scale_is_rejected() -> None:
    with pytest.raises(ValidationError, match="empty scale"):
        framework(scale=())


def test_valid_scores_pass() -> None:
    framework().validate_scores(
        {"structures_consultation": "G", "uses_clear_language": "A"}
    )


def test_unknown_competency_is_rejected() -> None:
    with pytest.raises(UnknownCompetencyError, match="invented_skill"):
        framework().validate_scores({"invented_skill": "G"})


def test_off_scale_score_is_rejected() -> None:
    with pytest.raises(InvalidScoreError, match=r"\['R', 'A', 'G'\]"):
        framework().validate_scores({"structures_consultation": "excellent"})


def test_a_custom_scale_is_honoured() -> None:
    """An organisation or employer may mark on something other than RAG."""
    fw = framework(scale=("fail", "pass", "merit"))
    fw.validate_scores({"structures_consultation": "merit"})
    with pytest.raises(InvalidScoreError):
        fw.validate_scores({"structures_consultation": "G"})


def test_a_schema_only_framework_accepts_any_scores() -> None:
    """Frameworks whose shape is described by a schema are not score-checked."""
    fw = CompetencyFramework(
        id="schema-only-v1",
        label="Schema only",
        result_schema={"type": "object", "properties": {"overall": {"type": "string"}}},
    )
    assert fw.competencies == ()
    fw.validate_scores({"anything_at_all": "whatever"})


def test_the_framework_holds_shape_and_says_nothing_about_which_model_runs() -> None:
    """The split the design depends on: no model, effort or threshold here.

    ``system_prompt`` is the one thing that looks like scoring and is not: the
    marking instructions are written by whoever wrote the rubric, and a rubric
    whose prompt lived somewhere else could not be authored through an API at
    all. Which model reads that prompt is still entirely the policy's business.
    """
    fields = set(CompetencyFramework.model_fields)
    assert fields == {
        "id",
        "label",
        "version",
        "domains",
        "competencies",
        "scale",
        "rating",
        "rating_field",
        "field_roles",
        "result_schema",
        "system_prompt",
    }
    assert not fields & {"primary_model", "primary_reasoning_effort", "timeout_s"}


def test_the_policy_holds_scoring_and_says_nothing_about_shape() -> None:
    """The mirror of the rule above: exactly one home for result shape."""
    from osce_assessment.contracts import EvaluationPolicy

    fields = set(EvaluationPolicy.model_fields)
    assert not fields & {
        "domains",
        "competencies",
        "scale",
        "result_schema",
        "schema_template",
    }
    assert {"primary_model", "system_prompt_override", "version"} <= fields
    assert "framework_id" in fields, "a policy must name the shape it scores"


# --- native ratings -------------------------------------------------------------
#
# Each rubric marks in its own units: a number in a range, a whole number in a
# range, a competent true/false, or a word on a scale. The framework checks the
# value the rubric defines rather than forcing everything through R/A/G.


def test_a_rag_rating_accepts_its_letters_and_refuses_any_other() -> None:
    fw = framework(scale=("G", "A", "R"), rating=Rating(kind="rag"))
    fw.validate_scores({"structures_consultation": "G", "uses_clear_language": "R"})
    for bad in ("B", "g", 1, None):
        with pytest.raises(InvalidScoreError, match=r"one of \['G', 'A', 'R'\]"):
            fw.validate_scores({"structures_consultation": bad})


def test_a_scale_rating_accepts_only_the_authors_words() -> None:
    fw = framework(scale=("Excellent", "Adequate", "Poor"), rating=Rating(kind="scale"))
    fw.validate_scores({"structures_consultation": "Adequate"})
    with pytest.raises(InvalidScoreError, match="one of"):
        fw.validate_scores({"structures_consultation": "Good"})


def test_an_integer_range_refuses_a_value_above_its_maximum() -> None:
    fw = framework(scale=(), rating=Rating(kind="range", minimum=0, maximum=10, step="integer"))
    fw.validate_scores({"structures_consultation": 0, "uses_clear_language": 10})
    for bad in (11, -1):
        with pytest.raises(InvalidScoreError, match="a whole number from 0 to 10"):
            fw.validate_scores({"structures_consultation": bad})


def test_a_range_rating_needs_both_bounds_lowest_first() -> None:
    with pytest.raises(ValidationError, match="needs a minimum and a maximum"):
        Rating(kind="range", maximum=10)
    with pytest.raises(ValidationError, match="must be below its maximum"):
        Rating(kind="range", minimum=10, maximum=0)


def test_a_nullable_domain_may_be_left_null() -> None:
    fw = framework(
        scale=(),
        rating=Rating(kind="range", minimum=0, maximum=10, step="integer"),
        rating_field="score",
        domains=(DOMAIN, CompetencyDomain(id="tasks", label="Tasks", nullable=True)),
    )
    result = {"global_skills": {"structures_consultation": {"score": 6}}, "tasks": None}
    assert fw.scores_in(result) == {"structures_consultation": 6}
    fw.validate_scores(fw.scores_in(result))
    assert [domain.nullable for domain in fw.domains] == [False, True]


def test_field_roles_come_from_a_closed_list() -> None:
    fw = framework(rating_field="score", field_roles={"missed": "improvement", "critical_flags": "flag"})
    assert fw.role_of("missed") == "improvement"
    assert fw.role_of("score") == "rating"
    assert fw.role_of("anything_else") == "other"
    with pytest.raises(ValidationError):
        framework(field_roles={"missed": "weakness"})


def test_the_rating_field_cannot_be_given_another_role() -> None:
    with pytest.raises(ValidationError, match="gives its rating field 'score' the role 'evidence'"):
        framework(rating_field="score", field_roles={"score": "evidence"})


def test_a_v1_payload_without_the_new_keys_keeps_rating_on_rag() -> None:
    """Today's platform-api payload: no rating, rating_field or field_roles."""
    fw = CompetencyFramework.model_validate(
        {
            "id": "v1",
            "label": "V1",
            "scale": ["G", "A", "R"],
            "domains": [{"id": "global_skills", "label": "Global skills"}],
            "competencies": [{"id": "structures_consultation", "label": "S", "domain_id": "global_skills"}],
        }
    )
    assert (fw.rating.kind, fw.rating_field, fw.field_roles) == ("rag", None, {})
    assert fw.scores_in({"global_skills": {"structures_consultation": {"score": "Q"}}}) == {}


def test_a_key_the_payload_should_not_carry_is_refused() -> None:
    with pytest.raises(ValidationError, match="labels"):
        CompetencyFramework.model_validate(
            {"id": "x", "label": "X", "rating": {"kind": "rag", "labels": {"G": "Competent"}}}
        )


def test_a_range_rating_accepts_numbers_within_its_bounds_only() -> None:
    fw = framework(scale=(), rating=Rating(kind="range", minimum=0, maximum=1))
    fw.validate_scores({"structures_consultation": 0.75, "opens_consultation": 1})
    for bad in (1.5, -0.1, "G", True):
        with pytest.raises(InvalidScoreError, match="a number from 0"):
            fw.validate_scores({"structures_consultation": bad})


def test_an_integer_range_refuses_a_fraction() -> None:
    fw = framework(scale=(), rating=Rating(kind="range", minimum=0, maximum=10, step="integer"))
    fw.validate_scores({"structures_consultation": 7})
    with pytest.raises(InvalidScoreError, match="a whole number from 0"):
        fw.validate_scores({"structures_consultation": 7.5})


def test_a_boolean_rating_accepts_only_true_or_false() -> None:
    fw = framework(scale=(), rating=Rating(kind="boolean"))
    fw.validate_scores({"structures_consultation": True, "uses_clear_language": False})
    with pytest.raises(InvalidScoreError, match="true or false"):
        fw.validate_scores({"structures_consultation": 1})


def test_an_enumerated_rating_still_needs_a_scale() -> None:
    with pytest.raises(ValidationError, match="empty scale"):
        framework(scale=(), rating=Rating(kind="rag"))


def test_ratings_are_read_out_of_a_result_by_the_rating_field() -> None:
    """Qualified ids find their answer under the domain by the local name."""
    clinical = CompetencyDomain(id="clinical", label="Clinical", nullable=True)
    portfolio = CompetencyDomain(id="portfolio", label="Portfolio", nullable=True)
    fw = CompetencyFramework(
        id="ortho-like",
        label="Ortho-like",
        scale=(),
        rating=Rating(kind="range", minimum=0, maximum=10, step="integer"),
        rating_field="score",
        domains=(clinical, portfolio),
        competencies=(
            Competency(id="clinical.awareness", label="Awareness", domain_id="clinical"),
            Competency(id="portfolio.awareness", label="Awareness", domain_id="portfolio"),
        ),
    )
    result = {
        "clinical": {"awareness": {"score": 8, "score_justification": "Good."}},
        "portfolio": None,
    }
    assert fw.scores_in(result) == {"clinical.awareness": 8}
    fw.validate_scores(fw.scores_in(result))


def test_a_framework_without_a_rating_field_reads_no_ratings() -> None:
    assert framework().scores_in({"global_skills": {"structures_consultation": {"score": "G"}}}) == {}


def test_a_fifth_exam_needs_no_code_only_a_framework() -> None:
    """A made-up exam: whole 1..5 ratings, a domain-level list, a narrative.

    Nothing in the engine names it; the rating kind and field carry everything
    the framework needs to check a mark in the exam's own units.
    """
    fw = CompetencyFramework.model_validate(
        {
            "id": "fifth-exam-v1",
            "label": "Fifth exam",
            "scale": [],
            "rating": {"kind": "range", "minimum": 1, "maximum": 5, "step": "integer"},
            "rating_field": "rating",
            "domains": [{"id": "consulting", "label": "Consulting"}],
            "competencies": [
                {"id": "consulting.opening", "label": "Opening", "domain_id": "consulting"},
                {"id": "consulting.closing", "label": "Closing", "domain_id": "consulting"},
            ],
        }
    )
    mark = {
        "consulting": {
            "opening": {"rating": 4, "evidence": "Introduced themselves."},
            "closing": {"rating": 2, "evidence": "No safety net."},
            "themes": ["Structure", "Safety netting"],
        },
        "narrative": "A solid consultation that ended abruptly.",
    }
    fw.validate_scores(fw.scores_in(mark))
    with pytest.raises(InvalidScoreError, match="a whole number from 1"):
        fw.validate_scores(fw.scores_in({"consulting": {"opening": {"rating": 6}}}))
