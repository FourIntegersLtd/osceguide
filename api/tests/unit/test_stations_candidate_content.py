"""The trainee-only projection of a station document (S1).

`GET /orgs/{slug}/stations` admits every rostered trainee, and the document is
the patient's persona and the examiner's material as much as it is the brief.
These pin the pure rule; `tests/http/test_stations_routes.py` pins it to the
route and its roles.
"""

from __future__ import annotations

from app.features.attempts import domain_material
from app.features.stations import domain_content, service_versions

FULL = {
    "reading_brief": "Mrs Patel, 42, chest pain for two days.",
    "candidate_brief": "Older spelling of the same brief.",
    "clinical_scenario": "A GP consultation.",
    "duration_minutes": 10,
    "doctor_information": {"doctor_task": "Take a history."},
    "patient_gender": "female",
    "patient_information": {
        "patient_biodata": "Mrs Patel, 42",
        "gender": "female",
        "persona": "anxious, guards the diagnosis",
        "opening_sentence": "Doctor, is it my heart?",
        "expanded_history": "The hidden block.",
    },
    "patient_brief": "You are unwell and know why.",
    "management_plan": {"explanation": "The model answer."},
    "examiner_additional_info": ["Mark the ICE."],
    "key_learning_points": ["Red flags"],
    "a_key_no_exam_has_invented_yet": "tomorrow's leak",
}


def test_a_trainee_keeps_the_briefs_the_scenario_and_the_doctors_information() -> None:
    projected = domain_content.candidate_content(FULL)
    assert projected is not None
    assert projected["reading_brief"] == FULL["reading_brief"]
    assert projected["candidate_brief"] == FULL["candidate_brief"]
    assert projected["clinical_scenario"] == FULL["clinical_scenario"]
    assert projected["duration_minutes"] == 10
    assert projected["doctor_information"] == FULL["doctor_information"]
    assert projected["patient_gender"] == "female"


def test_of_the_patient_block_only_the_identity_lines_survive() -> None:
    """What `PatientIdentityRead` discloses on a candidate's own brief read —
    the name line and the gender, never the persona or the hidden history."""
    projected = domain_content.candidate_content(FULL)
    assert projected is not None
    assert projected["patient_information"] == {"patient_biodata": "Mrs Patel, 42", "gender": "female"}


def test_the_patients_and_the_examiners_material_never_survives() -> None:
    projected = domain_content.candidate_content(FULL)
    assert projected is not None
    for key in (
        "patient_brief",
        "management_plan",
        "examiner_additional_info",
        "key_learning_points",
        "a_key_no_exam_has_invented_yet",
    ):
        assert key not in projected
    assert "persona" not in projected["patient_information"]
    assert "opening_sentence" not in projected["patient_information"]
    assert "expanded_history" not in projected["patient_information"]


def test_the_allowlist_is_a_rule_not_a_denylist() -> None:
    """A key nobody has seen before is stripped: a station gains keys as exams
    are added, and 'everything except the patient block' would hand each new
    one over by default."""
    assert domain_content.candidate_content({"brand_new_block": {"secret": True}}) == {}


def test_a_patient_block_with_no_identity_in_it_is_dropped_whole() -> None:
    assert domain_content.candidate_content({"patient_info": {"persona": "anxious"}}) == {}


def test_a_station_with_no_version_has_no_document() -> None:
    """`None` rather than `{}`: an empty dict reads as a document that was
    written and blanked."""
    assert domain_content.candidate_content(None) is None


# --------------------------------------------------------------------------
# The mirror is pinned to what it mirrors
# --------------------------------------------------------------------------


def test_the_candidate_keys_mirror_the_attempt_brief_read() -> None:
    """The same document vocabulary, owned by two slices.

    `attempts/domain_material.py` decides what a candidate reads through their
    attempt; `stations/domain_content.py` decides what a trainee-only reader of
    the org list gets. They may not drift, or one route would disclose what the
    other was written to withhold — the same arrangement the shared
    `unknown_exam` code has.
    """
    assert domain_content.SCENARIO_KEYS == domain_material.SCENARIO_KEYS
    assert domain_content.PATIENT_BLOCKS == domain_material.PATIENT_BLOCKS
    assert service_versions.BRIEF_KEY in domain_content.BRIEF_KEYS


def test_the_projection_discloses_nothing_the_review_owns() -> None:
    """The management plan and the teaching keys are the debrief: readable
    once a consultation is over, and not one moment before."""
    review_only = set(domain_material.TEACHING_KEYS) | {"management_plan", "patient_brief"}
    assert not review_only & domain_content.CANDIDATE_FACING_KEYS
