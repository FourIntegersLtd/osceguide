"""The committed seed file must be something the rubric authoring accepts.

`seeds/platform-starter.json` is what makes a migrated database usable: the
four consumer exams, each with the rubric b2c has been marking against. It is
generated from the captured legacy schemas, and the generator has already been
wrong once — the legacy models nest competencies inside a domain, so two
domains could use one name, which `parse_structure` refuses.

Nothing else catches that. The seeder is a script, so a broken file fails at
the moment somebody is setting up a database and has nothing else to go on.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.features.rubrics import domain as rubrics
from app.features.rubrics.schema_builder import derive_result_schema

SEED = Path(__file__).resolve().parents[2] / "seeds/platform-starter.json"
EXAMS = json.loads(SEED.read_text())["exams"]
CODES = [exam["code"] for exam in EXAMS]


def test_the_seed_covers_the_four_consumer_exams() -> None:
    assert sorted(CODES) == ["casc", "ortho", "plab", "sca"]


@pytest.mark.parametrize("exam", EXAMS, ids=CODES)
def test_every_rubric_in_the_seed_can_be_authored(exam: dict) -> None:
    assert exam["rubric"]["structure"]["schemaVersion"] == 2, exam["code"]
    structure = rubrics.parse_structure(exam["rubric"]["structure"])
    assert structure.domains, f"{exam['code']} would be marked against nothing"
    rubrics.validate_pacing(exam["rubric"]["pacing"])


@pytest.mark.parametrize("exam", EXAMS, ids=CODES)
def test_every_rubric_derives_a_result_schema(exam: dict) -> None:
    """The schema the model is constrained by is derived from the structure,
    so an unusable structure is an exam nothing can be marked against."""
    schema = derive_result_schema(rubrics.parse_structure(exam["rubric"]["structure"]))
    assert schema["properties"], exam["code"]


@pytest.mark.parametrize("exam", EXAMS, ids=CODES)
def test_every_rubric_carries_the_marking_prompt(exam: dict) -> None:
    # An empty prompt is a rubric that marks on the schema alone, which is not
    # what any of these exams has ever done.
    assert len(exam["rubric"]["system_prompt"].strip()) > 500, exam["code"]


def _domains(exam: dict) -> list[dict]:
    """The domain sections of an exam's seeded rubric."""
    return [section for section in exam["rubric"]["structure"]["sections"] if section["kind"] == "domain"]


def test_a_competency_id_is_unique_within_its_domain() -> None:
    """Ortho reuses fifteen competency names across its four domains, as the legacy model does.

    Version 2 qualifies a competency by its domain, so the names stay as the
    model wrote them; only a repeat inside one domain would be ambiguous.
    """
    for exam in EXAMS:
        for domain in _domains(exam):
            ids = [competency["id"] for competency in domain["competencies"]]
            assert len(ids) == len(set(ids)), f"{exam['code']}.{domain['id']} repeats a competency id"


def test_every_exam_is_marked_with_its_own_prompt() -> None:
    """CASC was marked with the RCGP GP prompt for years (C-1). No exam borrows another's."""
    for exam in EXAMS:
        assert "prompt_warning" not in exam["rubric"]
    casc = next(exam for exam in EXAMS if exam["code"] == "casc")
    assert casc["rubric"]["prompt_source"] == "casc_system.txt"
    assert "Royal College of Psychiatrists CASC examiner" in casc["rubric"]["system_prompt"]
    assert "RCGP" not in casc["rubric"]["system_prompt"]


@pytest.mark.parametrize("exam", EXAMS, ids=CODES)
def test_every_competency_carries_the_legacy_wording(exam: dict) -> None:
    """The model read each competency's legacy description; a label alone marks blind."""
    for domain in _domains(exam):
        assert domain["instructions"], f"{exam['code']}.{domain['id']}"
        for competency in domain["competencies"]:
            assert competency["instructions"], f"{exam['code']}.{competency['id']}"


def test_sca_keeps_its_score_anchors() -> None:
    """Only SCA's legacy models said what earns G, A and R; they must survive as descriptors."""
    sca = next(exam for exam in EXAMS if exam["code"] == "sca")
    competencies = {
        competency["id"]: competency for domain in _domains(sca) for competency in domain["competencies"]
    }

    assert len(competencies) == 29
    assert all(list(competency["descriptors"]) == ["G", "A", "R"] for competency in competencies.values())
    assert competencies["discovers_ice"]["descriptors"]["A"] == (
        "Explores two ICE elements but misses opportunities."
    )
    assert "Key aspects:" in competencies["discovers_ice"]["instructions"]


def test_the_committed_seed_is_what_the_generator_writes() -> None:
    """A hand edit to the seed is lost on the next regeneration, and a generator fix never ships without one.

    Both happened: SCA's live domains were set by hand in the file, and the
    acronym fix to `humanise` never reached it, so staging still read "Discovers ice".
    """
    script = SEED.parents[1] / "scripts/generate_platform_seed.py"
    spec = importlib.util.spec_from_file_location("generate_platform_seed", script)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generated, _ = generator.build()
    assert generated == json.loads(SEED.read_text())


def test_sca_marks_tasks_and_relating_live_and_reads_ice_as_initials() -> None:
    sca = next(exam for exam in EXAMS if exam["code"] == "sca")
    domains = {
        section["id"]: section
        for section in sca["rubric"]["structure"]["sections"]
        if section["kind"] == "domain"
    }
    assert {domain_id for domain_id, section in domains.items() if section["live"]} == {
        "tasks",
        "relating_to_others",
    }
    labels = {
        competency["id"]: competency["label"]
        for section in domains.values()
        for competency in section["competencies"]
    }
    assert labels["discovers_ice"] == "Discovers ICE"
    assert labels["shares_ice_plan"] == "Shares ICE plan"
