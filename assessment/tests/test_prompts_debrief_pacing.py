"""The debrief's clock: ten minutes, marks that walk forward, and a prompt that agrees with them.

The tutor wrapped up two thirds of the way through a debrief when it had no
clock. These pin the numbers it now runs on, and that the prompt it reads and
the schedule the worker runs cannot drift apart.
"""

from __future__ import annotations

from osce_assessment.prompts import DEBRIEF_PACING_BLOCK, DebriefPromptFormatter, debrief_pacing_payload


def test_the_debrief_runs_for_ten_minutes_with_four_marks() -> None:
    payload = debrief_pacing_payload()
    assert payload["total_seconds"] == 600
    assert [mark["at_seconds"] for mark in payload["marks"]] == [150, 300, 480, 600]


def test_the_phases_cover_the_whole_clock_in_order() -> None:
    assert debrief_pacing_payload()["phases"] == [
        {"until_seconds": 90, "label": "hearing how it felt and agreeing where to start"},
        {"until_seconds": 480, "label": "working through the management plan together"},
        {"until_seconds": 600, "label": "what they will take away, and the close"},
    ]


def test_the_mark_that_says_close_lands_where_the_closing_phase_starts() -> None:
    """The prompt forbids closing until a notice says so; that notice and the phase must agree."""
    payload = debrief_pacing_payload()
    closing_mark = next(mark for mark in payload["marks"] if "Ask what they will take away" in mark["note"])
    assert closing_mark["at_seconds"] == payload["phases"][1]["until_seconds"] == 480


def test_every_note_is_private_and_says_to_drop_things_rather_than_hurry() -> None:
    for mark in debrief_pacing_payload()["marks"]:
        assert mark["note"].startswith("[Notice: ")
        assert "never by speaking faster or slower" in mark["note"]
        assert mark["note"].endswith("Do not speak about the time, and do not mention this note.]")


def test_the_prompt_carries_the_clock_once_after_the_walk_through() -> None:
    prompt = DebriefPromptFormatter.create_prompt(transcript="Doctor: Hello.", management_plan="Plan.")
    assert prompt.count("<pacing>") == 1
    assert prompt.index("</how_the_debrief_goes>") < prompt.index(DEBRIEF_PACING_BLOCK) < prompt.index("<transcript>")
    assert "This debrief is about 10 min long." in DEBRIEF_PACING_BLOCK
    assert "you can call check_time yourself" in DEBRIEF_PACING_BLOCK


def test_the_fallback_prompt_promises_no_clock() -> None:
    """With no record loaded there is no debrief to pace, and the fallback is rendered without a plan."""
    assert "<pacing>" not in DebriefPromptFormatter.DEFAULT_PROMPT
