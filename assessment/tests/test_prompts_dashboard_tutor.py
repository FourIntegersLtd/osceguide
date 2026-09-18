"""The remembering tutor renders from a brief alone, and claims nothing the brief does not say."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from osce_assessment.prompts import DashboardTutorFormatter
from osce_assessment.prompts import _tutor_brief as brief_rendering

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TOOLS = {"recall": "recall_history", "search": "search_material", "suggest": "suggest_material", "remember": "remember"}
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
