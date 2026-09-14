"""Pure templates and the FAQ search (ported oracles from the legacy suite)."""

from __future__ import annotations

from livekit_assistant_worker.faq import search_common_queries
from livekit_assistant_worker.prompts import HelpInstructions, OnboardingInstructions, build_help_instructions, build_onboarding_instructions, build_onboarding_scene_update, greeting_for, instruction_header
from livekit_assistant_worker.prompts.help import format_phrase_lists_for_prompt


def test_faq_only_help_prompt_disables_screen_tools() -> None:
    prompt = HelpInstructions().get_help_instructions(screen_ui_guidance=False)
    assert "FAQ-only voice session (mandatory)" in prompt
    assert "Do NOT call the computer tool" in prompt
    assert "search_help_faqs" in prompt
    assert instruction_header(screen_ui_guidance=False) in prompt


def test_screen_guidance_help_prompt_carries_the_navigation_rules_and_phrase_lists() -> None:
    prompt = HelpInstructions().get_help_instructions(screen_ui_guidance=True)
    assert "GUIDED NAVIGATION" in prompt and "HANDS-OFF NAVIGATION" in prompt
    assert "offer_navigation_modes" in prompt
    assert format_phrase_lists_for_prompt() in prompt
    assert "the tool announces progress to the user automatically" in prompt


def test_onboarding_phases() -> None:
    intro = OnboardingInstructions(question="", patient_line="", phase="intro", user_name="amina").get_onboarding_instructions()
    assert "Hello, Doctor Amina!" in intro and "INTRODUCTION phase" in intro
    demo = OnboardingInstructions(question="How would you respond?", patient_line="I'm scared.", phase="demo", user_name="").get_onboarding_instructions()
    assert "The patient says: 'I'm scared.'" in demo and "How would you respond?" in demo and "DEMO scenario" in demo


def test_gpt_live_instructions() -> None:
    help_i = build_help_instructions()
    assert "search_help_faqs" in help_i.backend and "Athena" in help_i.voice and help_i.opening
    onboarding = build_onboarding_instructions(phase="intro", user_name="sam", question=None, patient_line=None)
    assert "The user's name is Sam." in onboarding.voice and "introduction phase" in onboarding.voice
    context, commentary = build_onboarding_scene_update(question="Q?", patient_line="Line")
    assert "Patient says: Line Learner prompt: Q?" in context and commentary


def test_greetings_by_session_type() -> None:
    assert greeting_for("help").startswith("Hi, I'm Athena")
    assert greeting_for("athena-doctor").startswith("Hello, I'm Doctor Athena")
    assert greeting_for("dashboard").startswith("Hello doctor. Based on your recent consultations")
    assert greeting_for("unknown") == "Hello doctor, I'm ready when you are."


# --- FAQ search (legacy oracle) ---------------------------------------------------


def test_ai_practice_query_returns_relevant_match() -> None:
    text, count = search_common_queries("Where is AI Practice?")
    assert count >= 1 and "AI Practice" in text and len(text) < 2000


def test_create_session_query_returns_relevant_match() -> None:
    text, count = search_common_queries("How do I create a session?")
    assert count >= 1 and ("Create Session" in text or "session" in text.lower())


def test_marketplace_query_returns_relevant_match() -> None:
    text, count = search_common_queries("Marketplace")
    assert count >= 1 and "Marketplace" in text


def test_empty_and_unrelated_queries() -> None:
    assert search_common_queries("   ") == (search_common_queries("   ")[0], 0) and "No search query" in search_common_queries("   ")[0]
    text, count = search_common_queries("xyzzy plugh completely unrelated gibberish")
    assert count == 0 and "No matching FAQs" in text
