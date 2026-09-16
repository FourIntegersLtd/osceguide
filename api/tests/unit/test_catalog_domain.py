"""The four exams, and what an organisation offering one means.

`app_type` in b2c and `b2b_exams` in b2b are two different concepts that share
a word: a published framework, and an institution's programme offering one.
ADR 0011 splits them; these tests hold the split.
"""

from __future__ import annotations

import pytest

from app.features.catalog import domain


def test_the_four_published_exams_are_known() -> None:
    assert {e.code for e in domain.PUBLISHED_EXAMS} == {"sca", "plab", "casc", "ortho"}


@pytest.mark.parametrize(
    ("code", "framework_id"),
    [
        ("sca", "sca-rcgp-v1"),
        ("plab", "plab2-gmc-v1"),
        ("casc", "casc-rcpsych-v1"),
        ("ortho", "ortho-frcs-v1"),
    ],
)
def test_each_exam_binds_the_engine_framework_the_legacy_shim_mapped(code: str, framework_id: str) -> None:
    """Oracle: `osce_assessment.compat.legacy_app_types`, which exists only to
    map these and is deleted once the migration has run."""
    assert domain.exam_by_code(code).framework_id == framework_id


def test_an_unknown_exam_code_is_refused_rather_than_guessed() -> None:
    with pytest.raises(domain.UnknownExam):
        domain.exam_by_code("mrcp")


@pytest.mark.parametrize("raw", ["  SCA ", "Sca", "SCA"])
def test_exam_codes_are_normalised(raw: str) -> None:
    assert domain.exam_by_code(raw).code == "sca"


def test_every_exam_carries_the_timings_the_station_runs_on() -> None:
    """b2c held these in a constants table keyed by app_type; they belong to
    the exam, so a fifth exam is a row rather than another lookup table."""
    for exam in domain.PUBLISHED_EXAMS:
        assert exam.default_reading_seconds > 0
        assert exam.default_simulation_seconds > 0


def test_sca_and_plab_have_the_durations_the_legacy_constants_declared() -> None:
    """Oracle: `b2c/shared/constants/shared_constants.py:225-231`."""
    assert domain.exam_by_code("sca").default_simulation_seconds == 15 * 60
    assert domain.exam_by_code("plab").default_simulation_seconds == 10 * 60
    assert domain.exam_by_code("casc").default_simulation_seconds == 10 * 60
    assert domain.exam_by_code("ortho").default_simulation_seconds == 11 * 60


def test_a_programme_is_an_organisation_offering_an_exam() -> None:
    programme = domain.ProgrammeRef(exam_code="plab", status="active")
    assert programme.is_offerable


def test_a_draft_programme_is_not_yet_offerable() -> None:
    assert not domain.ProgrammeRef(exam_code="plab", status="draft").is_offerable


def test_the_seed_migration_matches_the_published_exams() -> None:
    """The four rows are inserted by a migration and described in the domain.

    Two lists that must agree: a disagreement is a foreign key pointing at an
    exam the code does not believe exists, discovered at runtime.
    """
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "alembic/versions/c691f57ba7eb_catalog_and_stations.py"
    spec = importlib.util.spec_from_file_location("seed_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    seeded = {
        (code, framework_id, reading, simulation)
        for code, _name, framework_id, reading, simulation in module.SEED_EXAMS
    }
    declared = {
        (e.code, e.framework_id, e.default_reading_seconds, e.default_simulation_seconds)
        for e in domain.PUBLISHED_EXAMS
    }
    assert seeded == declared
