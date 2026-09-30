"""Generation profile hint and system prompt resolution."""

from __future__ import annotations

from app.core.exam_settings import ExamSettings
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
    prompt = resolve_system_prompt(structure, exam_settings=ExamSettings())
    assert "UK primary care" in prompt


def test_an_exam_that_names_no_prompt_is_not_written_as_sca() -> None:
    """A new exam's `{}` settings get the exam-neutral prompt, not SCA's GP consultation."""
    from app.features.stations.generation_profiles.resolve import resolve_system_prompt

    prompt = resolve_system_prompt({}, exam_settings=ExamSettings())
    assert prompt.startswith("You are an experienced clinical examiner writing an OSCE station")
    assert "UK primary care" not in prompt


def test_the_exams_own_station_prompt_applies_when_the_template_names_none() -> None:
    from app.features.stations.generation_profiles.resolve import resolve_system_prompt

    settings = ExamSettings.model_validate(
        {
            "generation": {
                "default_profile": "sca.station",
                "station_prompt_text": "  Write a PACES station.  ",
            }
        }
    )
    assert resolve_system_prompt({}, exam_settings=settings) == "Write a PACES station."


def test_a_profile_the_template_names_beats_the_exams_own_prompt() -> None:
    from app.features.stations.generation_profiles.resolve import resolve_system_prompt

    settings = ExamSettings.model_validate({"generation": {"station_prompt_text": "Write a PACES station."}})
    prompt = resolve_system_prompt({"generation": {"profileKey": "plab.station"}}, exam_settings=settings)
    assert "PLAB" in prompt
    assert "Write a PACES station." not in prompt


def test_a_templates_own_prompt_beats_everything_and_takes_the_append() -> None:
    from app.features.stations.generation_profiles.resolve import resolve_system_prompt

    settings = ExamSettings.model_validate({"generation": {"station_prompt_text": "Write a PACES station."}})
    structure = {
        "generation": {
            "profileKey": "custom",
            "systemPromptOverride": "Write a cardiology station.",
            "systemPromptAppend": "Use British spelling.",
        }
    }
    assert resolve_system_prompt(structure, exam_settings=settings) == (
        "Write a cardiology station.\n\nUse British spelling."
    )


def test_a_platform_template_may_carry_its_own_prompt() -> None:
    """Refused before 2026-09-30; a published template version is frozen, which is the safety."""
    from app.features.stations.station_validator import validate_generation_policy

    structure = {"generation": {"profileKey": "custom", "systemPromptOverride": "Write a PACES station."}}
    assert validate_generation_policy(structure) == []
    misplaced = {
        "generation": {"profileKey": "sca.station", "systemPromptOverride": "Write a PACES station."}
    }
    assert validate_generation_policy(misplaced) == [
        "structure.generation.systemPromptOverride is only allowed when profileKey is 'custom'"
    ]


def test_an_exams_own_summary_and_blog_text_win_over_their_keys() -> None:
    from app.features.generation import exam_prompts

    settings = ExamSettings.model_validate(
        {"generation": {"summary_prompt_text": "Summarise for PACES.", "blog_prompt_text": "   "}}
    )
    assert exam_prompts.summary_system_prompt(settings) == "Summarise for PACES."
    # Whitespace is no prompt: the key's built-in prompt applies.
    assert exam_prompts.blog_system_prompt(settings) == exam_prompts.GENERIC_BLOG_PROMPT
