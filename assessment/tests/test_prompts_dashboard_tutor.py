"""The remembering tutor renders from a brief alone, and claims nothing the brief does not say."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from osce_assessment.prompts import DashboardTutorFormatter
from osce_assessment.prompts import _tutor_brief as brief_rendering

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TOOLS = {"recall": "recall_history", "search": "search_material", "suggest": "suggest_material", "remember": "remember", "mark_done": "mark_done"}
LABELS = {"summaries": "A to Z", "slides": "Slides", "stations": "AI Practice"}


def _brief() -> dict:
    return json.loads((FIXTURES / "tutor" / "brief.json").read_text(encoding="utf-8"))


def _remembered(prompt: str) -> str:
    return prompt[prompt.index("<what_you_remember>") : prompt.index("</what_you_remember>")]


def test_the_brief_is_spoken_as_notes_about_named_consultations() -> None:
    prompt = DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS)
    remembered = _remembered(prompt)
    assert "Hip pain in a runner, two days ago." in remembered
    assert "Low mood after redundancy, about a week ago." in remembered
    assert "Chest pain on exertion, about a month ago." in remembered
    assert "clinical approach competent, clinical tasks needs work and relating to the patient strong" in remembered
    assert 'Something they said: "Come back if it does not improve"' in remembered
    assert "What was agreed: Name the examination out loud before the history ends and Say one follow-up timeframe in every plan" in remembered
    assert "You last spoke five days ago." in remembered
    assert "They said: Their exam is in about six weeks" in remembered
    assert "They read Anxiety, condition summary, yesterday." in remembered
    assert "They listened to Safety netting, episode three, about a week ago." in remembered


def test_nothing_in_the_notes_is_a_digit_or_a_letter_grade() -> None:
    """Ratings become words and dates become how long ago, because the whole thing is read aloud."""
    remembered = _remembered(DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS))
    assert not re.search(r"\d", remembered)
    assert not re.search(r"\b[RAG]\b", remembered)


def test_an_empty_brief_admits_it_rather_than_inventing_a_history() -> None:
    prompt = DashboardTutorFormatter.create_prompt({}, labels=LABELS)
    assert "You have nothing on file about this doctor yet" in prompt
    assert "Their recent consultations" not in prompt
    assert "You last spoke" not in prompt


def test_the_tutor_is_forbidden_to_speak_beyond_its_notes() -> None:
    prompt = DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS)
    assert "You must never:" in prompt
    assert "not in your notes below or in an answer a tool gave you" in prompt
    assert "invent a date, a rating, a score or a phrase the doctor said" in prompt
    assert "run a role-play consultation here" in prompt
    assert "You have already greeted them" in prompt


def test_the_tutor_knows_who_it_is_talking_to_and_where_they_are() -> None:
    prompt = DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS)
    who = prompt[prompt.index("<who_you_are_talking_to>") : prompt.index("</who_you_are_talking_to>")]
    assert "You are talking to Amara Okafor, who is preparing for the MRCGP SCA." in who
    assert "Use their first name once, early on" in who
    assert "Right now they are on the A to Z page." in who
    assert "From their menu they can open: Dashboard, AI Practice, A to Z, Slides." in who
    assert "/app/" not in who
    assert prompt.index("</who_you_are_talking_to>") < prompt.index("<what_you_remember>")


def test_a_brief_without_a_learner_or_screen_renders_no_who_block() -> None:
    bare = {k: v for k, v in _brief().items() if k not in ("learner", "screen")}
    assert "<who_you_are_talking_to>" not in DashboardTutorFormatter.create_prompt(bare, labels=LABELS)
    assert "<who_you_are_talking_to>" not in DashboardTutorFormatter.create_prompt({"learner": {}, "screen": {"navigation": "x"}})


def test_app_questions_search_help_and_done_steps_are_marked() -> None:
    prompt = DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS)
    assert "call search_material with the kind set to help" in prompt
    assert "call mark_done so your notes stop asking about it" in prompt
    without = {**_brief(), "tool_names": {k: v for k, v in TOOLS.items() if k != "mark_done"}}
    assert "mark_done" not in DashboardTutorFormatter.create_prompt(without, labels=LABELS)


def test_a_topic_they_came_with_opens_the_conversation() -> None:
    with_topic = {**_brief(), "topic": {"title": 'Asthma in "adults"', "kind": "summary"}}
    prompt = DashboardTutorFormatter.create_prompt(with_topic, labels=LABELS)
    assert f'They opened this conversation to talk about "Asthma in adults", which they were just looking at in {LABELS["summaries"]}.' in prompt
    assert "They came to talk about a subject, so start there" in prompt
    assert "Start from what you remember." not in prompt


def test_any_conversation_can_turn_into_a_topic_discussion_grounded_in_the_material() -> None:
    prompt = DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS)
    assert "<how_to_discuss_a_topic>" in prompt
    assert f"Call {TOOLS['search']} before you explain anything" in prompt
    assert "do not fill the gap yourself" in prompt
    assert "They opened this conversation to talk about" not in prompt
    assert "Start from what you remember." in prompt
    without_search = {**_brief(), "tool_names": {k: v for k, v in TOOLS.items() if k != "search"}}
    assert "<how_to_discuss_a_topic>" not in DashboardTutorFormatter.create_prompt(without_search, labels=LABELS)


def test_tools_are_named_from_the_brief_never_from_the_engine() -> None:
    renamed = {**_brief(), "tool_names": {"recall": "look_back", "search": "find_reading", "suggest": "put_on_screen", "remember": "keep"}}
    prompt = DashboardTutorFormatter.create_prompt(renamed, labels=LABELS)
    for name in ("look_back", "find_reading", "put_on_screen", "keep"):
        assert name in prompt
    for name in ("recall_history", "search_material", "suggest_material"):
        assert name not in prompt
    assert "call remember" not in prompt  # "remember" the word still appears in prose


def test_without_tools_the_tutor_is_told_it_cannot_look_anything_up() -> None:
    prompt = DashboardTutorFormatter.create_prompt({k: v for k, v in _brief().items() if k != "tool_names"}, labels=LABELS)
    assert "You have no way to look anything up" in prompt
    assert "call " not in prompt.split("<how_to_use_what_you_know>")[1]


def test_material_is_named_by_the_consumers_own_labels() -> None:
    prompt = DashboardTutorFormatter.create_prompt(_brief(), labels=LABELS)
    assert "such as A to Z or Slides" in prompt
    assert "a specific station from AI Practice" in prompt
    fallback = DashboardTutorFormatter.create_prompt(_brief())
    assert "the condition summaries" in fallback and "the practice stations" in fallback


def test_history_is_capped_so_the_prompt_stays_a_fixed_size() -> None:
    many = {
        "consultations": [{"title": f"Consultation number {i}", "days_ago": i, "improvements": [f"point {j}" for j in range(10)]} for i in range(20)],
        "debriefs": [{"title": f"Debrief {i}", "days_ago": i, "agreed_steps": ["a", "b", "c", "d", "e"]} for i in range(10)],
        "activity": [{"kind": "read", "title": f"Reading {i}", "days_ago": i} for i in range(30)],
        "facts": [f"fact {i}" for i in range(12)],
    }
    remembered = _remembered(DashboardTutorFormatter.create_prompt(many))
    assert remembered.count("Consultation number") == brief_rendering.MAX_CONSULTATIONS
    assert remembered.count("Debrief on ") == brief_rendering.MAX_DEBRIEFS
    assert remembered.count("They read Reading") == brief_rendering.MAX_ACTIVITIES
    assert remembered.count("They said: fact") == brief_rendering.MAX_FACTS
    assert remembered.count("point ") == brief_rendering.MAX_CONSULTATIONS * brief_rendering.MAX_ITEMS_EACH
    assert remembered.count("What was agreed: a, b and c") == brief_rendering.MAX_DEBRIEFS


def test_a_long_snippet_is_cut_at_the_budget() -> None:
    long = "word " * 100
    assert len(brief_rendering.snippet(long)) <= brief_rendering.MAX_SNIPPET_CHARS
    assert brief_rendering.snippet(long).endswith("…")


@pytest.mark.parametrize(
    ("days", "said"),
    [(0, "today"), (1, "yesterday"), (3, "three days ago"), (8, "about a week ago"), (16, "about two weeks ago"), (35, "about a month ago"), (95, "about three months ago"), (None, "recently"), ("x", "recently")],
)
def test_how_long_ago_is_said_not_counted(days, said) -> None:
    assert brief_rendering.when(days) == said


def test_malformed_entries_are_skipped_rather_than_raising() -> None:
    brief = {"consultations": ["not a dict", {"title": None, "domains": "A", "improvements": "Signpost"}], "facts": "not a list", "activity": None}
    remembered = _remembered(DashboardTutorFormatter.create_prompt(brief))
    assert "a consultation, recently." in remembered
    assert "Worth working on" not in remembered and "They said" not in remembered
