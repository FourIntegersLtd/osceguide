"""The frameworks the platform publishes."""

from __future__ import annotations

import pytest

from osce_assessment.catalog import (
    SCA_RCGP_V1,
    UnknownFrameworkError,
    all_frameworks,
    framework,
    framework_ids,
)
from osce_assessment.contracts import RAG_SCALE, CompetencyFramework


def test_the_four_platform_exams_are_published() -> None:
    assert set(framework_ids()) == {
        "sca-rcgp-v1",
        "plab2-gmc-v1",
        "casc-rcpsych-v1",
        "ortho-frcs-v1",
    }


def test_lookup_returns_the_published_framework() -> None:
    assert framework("sca-rcgp-v1") is SCA_RCGP_V1


def test_unknown_id_raises_and_names_what_is_known() -> None:
    with pytest.raises(UnknownFrameworkError) as excinfo:
        framework("employer-bespoke-v1")
    assert "sca-rcgp-v1" in str(excinfo.value)


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_every_published_framework_is_internally_consistent(
    fw: CompetencyFramework,
) -> None:
    """Construction validates shape, so this also guards future catalogue edits."""
    assert fw.id and fw.label
    assert fw.scale == RAG_SCALE
    assert len(set(fw.competency_ids)) == len(fw.competency_ids)
    for competency in fw.competencies:
        assert competency.domain_id in fw.domain_ids


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_every_published_framework_round_trips(fw: CompetencyFramework) -> None:
    assert CompetencyFramework.model_validate_json(fw.model_dump_json()) == fw


def test_sca_carries_the_domains_the_platform_marks_today() -> None:
    assert SCA_RCGP_V1.domain_ids == ("global_skills", "tasks", "relating_to_others")
    assert "structures_consultation" in SCA_RCGP_V1.competency_ids
    assert "uses_clear_language" in SCA_RCGP_V1.competency_ids
    SCA_RCGP_V1.validate_scores({"structures_consultation": "G"})


def test_the_catalogue_cannot_be_mutated_through_its_accessors() -> None:
    ids = framework_ids()
    frameworks = all_frameworks()
    assert isinstance(ids, tuple)
    assert isinstance(frameworks, tuple)
    assert framework_ids() == ids
    assert all_frameworks() == frameworks
