"""A peer room must expose legacy structured material to the correct role."""

from uuid import uuid4

from app.features.peer_practice.service_station import _station_payload
from app.features.stations.service_reads import VersionMaterial


def material(*, doctor=True, review=False):
    mat = VersionMaterial(
        version_id=uuid4(),
        station_id=uuid4(),
        title="Hair loss",
        exam_id=uuid4(),
        content={
            "doctor_information": {
                "patient_biodata": "Example patient",
                "recent_notes": ["Hair loss for 3 months"],
            },
            "patient_information": {
                "opening_sentence": "My hair is falling out",
                "expanded_history": "Started three months ago",
                "idea": ["Thyroid problem"],
                "concerns": ["Becoming bald"],
                "expectation": ["An explanation"],
                "persona": "Worried",
                "questions": ["Will it grow back?"],
            },
            "management_plan": {
                "explanation": "Discuss the likely cause",
                "safety_netting": "Arrange review",
            },
        },
    )
    return _station_payload(mat, is_doctor=doctor, reveal_review=review)


def test_doctor_reads_notes_without_hidden_actor_script_or_answers():
    result = material()
    assert result.doctor_information.recent_notes == ["Hair loss for 3 months"]
    assert result.patient_information is None
    assert result.patient_script is None
    assert result.management is None


def test_patient_receives_all_script_tabs():
    result = material(doctor=False)
    assert result.patient_information.opening_sentence == "My hair is falling out"
    assert result.patient_information.expanded_history == "Started three months ago"
    assert result.patient_information.concerns == ["Becoming bald"]
    assert result.patient_information.persona == "Worried"
    assert result.management is None


def test_debrief_reveals_structured_management_for_both_roles():
    for doctor in (True, False):
        result = material(doctor=doctor, review=True)
        assert result.management.explanation == "Discuss the likely cause"
        assert result.patient_information.idea == ["Thyroid problem"]


def test_fields_authored_as_null_read_as_not_given():
    mat = VersionMaterial(
        version_id=uuid4(),
        station_id=uuid4(),
        title="Rosacea",
        exam_id=uuid4(),
        content={"doctor_information": {"patient_biodata": "Daniel Cooper, 52", "recent_notes": None}},
    )
    result = _station_payload(mat, is_doctor=True, reveal_review=False)
    assert result.doctor_information.recent_notes == []
    assert result.doctor_information.patient_biodata == "Daniel Cooper, 52"
