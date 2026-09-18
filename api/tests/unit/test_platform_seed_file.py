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


def test_a_competency_id_is_unique_across_its_whole_rubric() -> None:
    """The failure the generator actually hit.

    Ortho reuses fifteen competency names across its four domains, which is
    legal in the legacy model and refused here, so the generator qualifies
    the clashing ones and records the original in `legacy_id`.
    """
    for exam in EXAMS:
        ids = [
            competency["id"]
            for domain in exam["rubric"]["structure"]["domains"]
            for competency in domain["competencies"]
        ]
        assert len(ids) == len(set(ids)), f"{exam['code']} repeats a competency id"


def test_a_disambiguated_competency_still_says_what_it_was_called() -> None:
    qualified = [
        competency
        for exam in EXAMS
        for domain in exam["rubric"]["structure"]["domains"]
        for competency in domain["competencies"]
        if "legacy_id" in competency
    ]
    assert qualified, "ortho's clashing ids should be recorded, not silently renamed"
    for competency in qualified:
        assert competency["id"].endswith(competency["legacy_id"])


def test_casc_records_that_it_is_marked_with_the_wrong_prompt() -> None:
    """Open question C-1, and live production behaviour.

    No CASC marking prompt exists anywhere, and both legacy backends mark it
    with the RCGP GP one. The seed reproduces that because the point is
    parity, but it must say so rather than let the next person assume a CASC
    rubric was ever written.
    """
    casc = next(exam for exam in EXAMS if exam["code"] == "casc")
    assert casc["rubric"]["prompt_source"] == "b2c_sca_system.txt"
    assert "C-1" in casc["rubric"]["prompt_warning"]
