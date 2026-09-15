"""FAQ ranking over a corpus the backend supplied (oracle ported from the legacy suite)."""

from __future__ import annotations

from livekit_assistant_worker.help_corpus import EMPTY_QUERY_MESSAGE, NO_MATCH_PREFIX, HelpCorpus, search
from livekit_assistant_worker.prompts import navigation_mode_prompt

CORPUS = HelpCorpus.model_validate({
    "entries": [
        {"section": "Getting started", "question": "Where is AI Practice?", "answer": "AI Practice is in the left navigation."},
        {"section": "Sessions", "question": "How do I create a session?", "answer": "Open AI Practice and click Create Session."},
        {"section": "Marketplace", "question": "What is the Marketplace?", "answer": "Marketplace lists shared stations."},
    ],
    "no_match_message": "Direct the user to Contact Us.",
})


def test_ai_practice_query_returns_relevant_match() -> None:
    text, count = search(CORPUS, "Where is AI Practice?")
    assert count >= 1 and text.startswith("Use ONLY the FAQ answers below. If none fit: Direct the user to Contact Us.")
    assert "[Getting started]" in text and "ANSWER: AI Practice is in the left navigation." in text


def test_best_match_is_ranked_first_and_limit_applies() -> None:
    text, count = search(CORPUS, "How do I create a session?", limit=1)
    assert count == 1 and "Create Session" in text and "Marketplace" not in text


def test_empty_and_unrelated_queries() -> None:
    assert search(CORPUS, "   ") == (EMPTY_QUERY_MESSAGE, 0)
    text, count = search(CORPUS, "xyzzy plugh completely unrelated gibberish")
    assert count == 0 and text == f"{NO_MATCH_PREFIX} Direct the user to Contact Us."


def test_an_empty_corpus_never_matches() -> None:
    assert search(HelpCorpus(), "Where is AI Practice?")[1] == 0


BRANDED = HelpCorpus.model_validate({
    "entries": [
        {"section": "Start", "question": "What is Acme Tutor?", "answer": "Acme Tutor is a practice platform."},
        {"section": "Pricing", "question": "Do I need to pay for Acme Tutor?", "answer": "Yes, Acme Tutor needs a subscription."},
        {"section": "Station", "question": "I finished but there is no feedback or transcript", "answer": "Wait a few minutes, then open the session."},
        {"section": "Station", "question": "Where is the consultation transcript?", "answer": "Open the session, then the Simulation tab."},
        {"section": "Station", "question": "Which tab has the transcript?", "answer": "The Simulation tab."},
    ],
    "no_match_message": "Direct the user to Contact Us.",
    "boilerplate": ["Acme Tutor", "Nova"],
})


def test_product_name_in_the_query_does_not_outrank_the_subject() -> None:
    """Seen in production: the model asked "how to find my transcript on <product>" and the
    two entries whose *question* names the product beat the transcript entries."""
    text, count = search(BRANDED, "how to find my transcript on Acme Tutor", limit=3)
    assert count == 3
    assert "What is Acme Tutor?" not in text and "pay for Acme Tutor" not in text
    assert "Where is the consultation transcript?" in text


def test_a_question_about_the_product_itself_still_matches() -> None:
    text, count = search(BRANDED, "what is Acme Tutor", limit=1)
    assert count == 1 and "What is Acme Tutor?" in text


def test_default_result_window_is_five() -> None:
    assert search(BRANDED, "transcript session tab feedback pay platform")[1] == 5


def test_a_question_about_the_persona_alone_still_matches_by_name() -> None:
    corpus = HelpCorpus.model_validate({
        "entries": [
            {"section": "Voice", "question": "Who is Nova?", "answer": "Nova is the voice assistant."},
            {"section": "Billing", "question": "Who do I email for billing?", "answer": "Email support."},
        ],
        "boilerplate": ["Nova"],
    })
    text, count = search(corpus, "who is Nova", limit=1)
    assert count == 1 and "Who is Nova?" in text


def test_navigation_mode_prompts() -> None:
    assert "perform_click" in navigation_mode_prompt("automate") and "Navigate for me" in navigation_mode_prompt("automate")
    assert "show_pointer" in navigation_mode_prompt("guide") and "Do not use perform_click" in navigation_mode_prompt("guide")
