"""Generation profile hint and system prompt resolution."""

from __future__ import annotations

from app.features.stations.generation_profiles.resolve import (
    effective_block_hints_for_profile,
    resolve_block_generation_hints,
)


def test_sca_capability_supplement_hint() -> None:
    structure = {
        "generation": {"profileKey": "sca.station"},
        "sections": [
            {
                "id": "clinical_experience_groups",
                "blocks": [{"id": "capability", "type": "singleSelect", "label": "Capability"}],
            },
        ],
    }
    hints = resolve_block_generation_hints(structure, profile_key="sca.station")
    assert "clinical experience group" in hints["capability"].lower()


def test_plab_management_examination_findings_supplement() -> None:
    structure = {
        "sections": [
            {
                "id": "management_plan",
                "blocks": [
                    {
                        "id": "management_examination_findings",
                        "type": "list",
                        "label": "Examination findings",
                    },
                ],
            },
        ],
    }
    hints = resolve_block_generation_hints(structure, profile_key="plab.station")
    assert "examination" in hints["management_examination_findings"].lower()


def test_asterix_investigation_field_supplements() -> None:
    structure = {
        "sections": [
            {
                "id": "sec_candidate_results",
                "blocks": [
                    {"id": "investigation_type", "type": "longText", "label": "Type"},
                    {"id": "recent_abnormal_results", "type": "list", "label": "Results"},
                    {"id": "past_results_trend", "type": "longText", "label": "Trend"},
                ],
            },
        ],
    }
    hints = resolve_block_generation_hints(structure, profile_key="sca.station")
    assert hints["investigation_type"]
    assert hints["recent_abnormal_results"]
    assert hints["past_results_trend"]


def test_effective_block_hints_includes_supplements_and_overrides() -> None:
    effective = effective_block_hints_for_profile("sca.station")
    assert "capability" in effective
    assert "opening_sentence" in effective
    assert "simulated patient" in effective["opening_sentence"].lower()


def test_sca_explanation_hint_includes_muaclw() -> None:
    structure = {
        "generation": {"profileKey": "sca.station"},
        "sections": [
            {
                "id": "mgmt",
                "blocks": [{"id": "explanation", "type": "longText", "label": "Explanation"}],
            },
        ],
    }
    hints = resolve_block_generation_hints(structure, profile_key="sca.station")
    assert "MUACLW" in hints.get("explanation", "")


def test_placeholder_appended_when_no_custom_hint() -> None:
    structure = {
        "generation": {"profileKey": "sca.station"},
        "sections": [
            {
                "id": "s",
                "blocks": [
                    {
                        "id": "idea",
                        "type": "list",
                        "label": "Ideas",
                        "placeholder": "Extra author note for AI",
                    },
                ],
            },
        ],
    }
    hints = resolve_block_generation_hints(structure, profile_key="sca.station")
    assert "Author guidance: Extra author note for AI" in hints["idea"]
    assert "Patient's thoughts" in hints["idea"] or "thoughts" in hints["idea"].lower()


def test_custom_generation_hint_wins() -> None:
    structure = {
        "sections": [
            {
                "id": "s",
                "blocks": [
                    {
                        "id": "explanation",
                        "type": "longText",
                        "label": "X",
                        "generationHint": "Only this",
                        "placeholder": "ignored",
                    },
                ],
            },
        ],
    }
    hints = resolve_block_generation_hints(structure, profile_key="sca.station")
    assert hints["explanation"] == "Only this"


def test_resolve_system_prompt_uses_profile() -> None:
    from app.features.stations.generation_profiles.resolve import resolve_system_prompt

    structure = {"generation": {"profileKey": "sca.station"}}
    prompt = resolve_system_prompt(structure, exam_code="sca", allow_custom_override=False)
    assert "UK primary care" in prompt
