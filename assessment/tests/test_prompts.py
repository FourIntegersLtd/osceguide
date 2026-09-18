"""Prompt text is data; the engine only loads and renders it."""

from __future__ import annotations

import pytest

from osce_assessment.prompts import (
    USER_PROMPT_TEMPLATE_ID,
    UnknownPromptError,
    available_prompt_ids,
    prompt_text,
    render_user_prompt,
)


def test_the_only_shipped_prompt_is_the_generic_user_template() -> None:
    """Marking instructions are authored per rubric, so none ship with the engine.

    Three exam-named .txt files used to sit here, chosen by a dict keyed on
    framework id. Adding an exam meant editing the package.
    """
    assert set(available_prompt_ids()) == {"feedback_evaluation_v1"}


def test_a_framework_carries_its_own_marking_instructions() -> None:
    from osce_assessment.contracts import CompetencyFramework

    assert "system_prompt" in CompetencyFramework.model_fields


def test_the_engine_does_not_choose_a_prompt_by_framework_id() -> None:
    import osce_assessment.prompts as prompts

    assert not hasattr(prompts, "default_system_prompt_id")


def test_user_prompt_renders_station_and_transcript() -> None:
    rendered = render_user_prompt(station_name="Chest pain", transcript="<DOCTOR>\nHi\n</DOCTOR>")
    assert "Chest pain" in rendered
    assert "<DOCTOR>\nHi\n</DOCTOR>" in rendered
    assert "DOCTOR (GP trainee under assessment)" in rendered


def test_user_prompt_template_explains_speaker_tags_before_the_instructions() -> None:
    text = prompt_text(USER_PROMPT_TEMPLATE_ID)
    assert text.index("Transcript speakers are tagged") < text.index("For each category")


def test_unknown_prompt_id_raises_with_known_ids() -> None:
    with pytest.raises(UnknownPromptError, match="feedback_evaluation_v1"):
        prompt_text("nope")
