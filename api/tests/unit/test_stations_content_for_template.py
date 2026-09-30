"""A b2c station bound to its exam's template renders each block from the nested section it lives in."""

from __future__ import annotations

from app.features.stations.domain_content import content_for_template

# The PLAB template's shape, cut down: the section ids are the b2c document's
# nested keys, and one block carries its section's prefix.
PLAB_SECTIONS = [
    {"id": "patient_information", "blocks": [{"id": "opening_sentence"}, {"id": "examination_findings"}]},
    {"id": "doctor_information", "blocks": [{"id": "patient_information"}, {"id": "task_instructions"}]},
    {
        "id": "management_plan",
        "blocks": [{"id": "management_examination_findings"}, {"id": "specialties"}],
    },
]


def test_nested_b2c_content_is_lifted_to_block_ids() -> None:
    """Each block reads its own section; the section dicts go, other keys stay."""
    stored = {
        "station_name": "Chest pain",
        "specialties": ["cardiology"],
        "patient_information": {
            "opening_sentence": "My chest hurts.",
            "examination_findings": "Pulse 92.",
            "idea": "Indigestion.",
        },
        "doctor_information": {
            "patient_information": "Mr Okafor, 54.",
            "task_instructions": "Take a history.",
        },
        "management_plan": {"examination_findings": "ECG: ST elevation."},
    }

    assert content_for_template(stored, PLAB_SECTIONS) == {
        "station_name": "Chest pain",
        "specialties": ["cardiology"],
        "opening_sentence": "My chest hurts.",
        "examination_findings": "Pulse 92.",
        "patient_information": "Mr Okafor, 54.",
        "task_instructions": "Take a history.",
        "management_examination_findings": "ECG: ST elevation.",
    }


def test_flat_content_is_left_as_stored() -> None:
    """A station authored against its template already holds its blocks flat."""
    stored = {"opening_sentence": "My chest hurts.", "reading_brief": "A man with chest pain."}

    assert content_for_template(stored, PLAB_SECTIONS) == stored
