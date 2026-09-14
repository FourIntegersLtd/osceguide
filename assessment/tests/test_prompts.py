"""Prompt text is data; the engine only loads and renders it."""

from __future__ import annotations

import pytest

from osce_assessment.catalog import all_frameworks
from osce_assessment.prompts import (
    USER_PROMPT_TEMPLATE_ID,
    UnknownPromptError,
    available_prompt_ids,
    default_system_prompt_id,
    prompt_text,
    render_user_prompt,
    system_prompt,
)


def test_the_shipped_prompt_ids() -> None:
    assert set(available_prompt_ids()) == {
        "feedback_evaluation_v1",
        "sca_feedback_assessment_v1",
        "plab_feedback_assessment_v1",
        "ortho_feedback_assessment_v1",
    }


@pytest.mark.parametrize("fw", all_frameworks(), ids=lambda fw: fw.id)
def test_every_published_framework_has_a_default_prompt_that_resolves(fw) -> None:
    assert system_prompt(default_system_prompt_id(fw.id)).strip()


def test_casc_is_marked_with_the_sca_prompt_by_design() -> None:
    """Neither backend ever had a CASC prompt; the fallthrough is now explicit."""
    assert default_system_prompt_id("casc-rcpsych-v1") == "sca_feedback_assessment_v1"
    assert default_system_prompt_id("sca-rcgp-v1") == "sca_feedback_assessment_v1"


def test_frameworks_do_not_carry_a_prompt_themselves() -> None:
    """Prompt choice is scoring, so it belongs to the policy, not the framework."""
    from osce_assessment.contracts import CompetencyFramework

    assert "system_prompt_id" not in CompetencyFramework.model_fields


def test_unknown_framework_has_no_default_prompt() -> None:
    with pytest.raises(UnknownPromptError, match="sca-rcgp-v1"):
        default_system_prompt_id("employer-bespoke-v1")


def test_system_prompts_are_substantial_and_role_framed() -> None:
    assert "<role>" in system_prompt("sca_feedback_assessment_v1")
    assert "PLAB" in system_prompt("plab_feedback_assessment_v1")
    assert len(system_prompt("ortho_feedback_assessment_v1")) > 10_000


def test_user_prompt_renders_station_and_transcript() -> None:
    rendered = render_user_prompt(station_name="Chest pain", transcript="<DOCTOR>\nHi\n</DOCTOR>")
    assert "Chest pain" in rendered
    assert "<DOCTOR>\nHi\n</DOCTOR>" in rendered
    assert "DOCTOR (GP trainee under assessment)" in rendered


def test_user_prompt_template_explains_speaker_tags_before_the_instructions() -> None:
    text = prompt_text(USER_PROMPT_TEMPLATE_ID)
    assert text.index("Transcript speakers are tagged") < text.index("For each category")


def test_unknown_prompt_id_raises_with_known_ids() -> None:
    with pytest.raises(UnknownPromptError, match="sca_feedback_assessment_v1"):
        prompt_text("nope")
