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


def test_the_framework_holds_shape_and_says_nothing_about_scoring() -> None:
    """The split the design depends on: no model, prompt or threshold here."""
    fields = set(CompetencyFramework.model_fields)
    assert fields == {
        "id",
        "label",
        "version",
        "domains",
        "competencies",
        "scale",
        "result_schema",
    }
    assert not fields & {"primary_model", "system_prompt_override", "timeout_s"}


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
