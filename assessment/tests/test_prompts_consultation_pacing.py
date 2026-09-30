"""The clock, and the one thing that must never drift: prompt text versus schedule.

Both the phase budgets the model reads and the marks the worker fires derive
from one ``ConsultationPacing``. If someone changes a duration and only half of
it moves, the doctor is told it has five and a half minutes for history while
the notice telling it to stop arrives at four. The parse-it-back test below is
what catches that.

The durations themselves are authored with a rubric and arrive as a payload, so
these tests build their own clocks rather than reading a shipped table.
"""

from __future__ import annotations

import json
import re

import pytest

from osce_assessment.prompts import (
    DEFAULT_PACING,
    AthenaDoctorFormatter,
    ConsultationPacing,
    InvalidPacingError,
    consultation_pacing_payload,
    pacing_from_payload,
)
from osce_assessment.prompts.consultation_pacing import human_duration

# Clocks an author might plausibly store: a long consultation, a short one, and
# one that is neither. Nothing here names an exam.
LONG = ConsultationPacing(total_seconds=720, history_seconds=360, introduction_seconds=30, safety_net_seconds=120)
SHORT = ConsultationPacing(total_seconds=480, history_seconds=240, introduction_seconds=20, safety_net_seconds=80)
MEDIUM = ConsultationPacing(total_seconds=600, history_seconds=300, introduction_seconds=30, safety_net_seconds=100)
CLOCKS = [LONG, SHORT, MEDIUM]


def test_a_stored_clock_round_trips_through_its_payload() -> None:
    assert pacing_from_payload(
        {
            "total_seconds": 720,
            "history_seconds": 360,
            "introduction_seconds": 30,
            "safety_net_seconds": 120,
        }
    ) == LONG


@pytest.mark.parametrize(
    ("broken", "because"),
    [
        ({"total_seconds": 0, "history_seconds": 1, "introduction_seconds": 1, "safety_net_seconds": 1}, "no time"),
        ({"total_seconds": 600, "history_seconds": 30, "introduction_seconds": 60, "safety_net_seconds": 100}, "introduction"),
        ({"total_seconds": 600, "history_seconds": 550, "introduction_seconds": 30, "safety_net_seconds": 100}, "safety netting"),
        ({"total_seconds": 600, "history_seconds": 300}, "four whole numbers"),
    ],
)
def test_a_clock_that_cannot_be_run_is_refused_rather_than_rendered(broken, because) -> None:
    """A mark out of order gives a phase a negative length and the model an impossible instruction."""
    with pytest.raises(InvalidPacingError):
        pacing_from_payload(broken)


@pytest.mark.parametrize("pacing", CLOCKS)
def test_the_phase_budgets_in_the_prompt_are_the_ones_the_clock_runs_on(pacing) -> None:
    """The anti-drift test: read the minutes back out of the rendered prompt."""
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {}, {"explanation": "x"}, pacing=pacing)
    budgets = dict(re.findall(r"^PHASE (\d) — [A-Z4 ]+\(~([\d.]+ (?:sec|min))", prompt, flags=re.MULTILINE))
    assert budgets["1"] == human_duration(pacing.introduction_seconds)
    assert budgets["2"] == human_duration(pacing.history_talk_seconds)
    assert budgets["3"] == human_duration(pacing.management_seconds)
    assert budgets["4"] == human_duration(pacing.safety_net_seconds)
    assert human_duration(pacing.total_seconds) in prompt, "and the whole length is stated once"


def test_a_shorter_station_changes_the_budgets_and_nothing_else() -> None:
    args = ("Hypothyroidism", {}, {"explanation": "x"})
    long_prompt = AthenaDoctorFormatter.create_prompt(*args, pacing=LONG)
    short_prompt = AthenaDoctorFormatter.create_prompt(*args, pacing=SHORT)
    differing = [a for a, b in zip(long_prompt.splitlines(), short_prompt.splitlines()) if a != b]
    assert differing, "the budgets do move"
    assert all("PHASE" in line or "This consultation is about" in line for line in differing)


def test_the_doctor_defaults_to_a_full_length_consultation() -> None:
    """Three positional args is how the bench and most callers still invoke it."""
    assert AthenaDoctorFormatter.create_prompt("Hypothyroidism", {}, {}) == AthenaDoctorFormatter.create_prompt(
        "Hypothyroidism", {}, {}, pacing=DEFAULT_PACING
    )


@pytest.mark.parametrize("pacing", CLOCKS)
def test_the_marks_walk_forward_and_stop_at_the_end(pacing) -> None:
    marks = [m["at_seconds"] for m in consultation_pacing_payload(pacing)["marks"]]
    total = pacing.total_seconds
    assert marks == sorted(marks) and len(set(marks)) == len(marks)
    assert marks[0] > 0 and marks[-1] == total, "the last word arrives at time, not after it"


@pytest.mark.parametrize("pacing", CLOCKS)
def test_every_note_says_to_drop_things_rather_than_hurry(pacing) -> None:
    """A clock the model reads as permission to talk faster would be worse than none."""
    for mark in consultation_pacing_payload(pacing)["marks"]:
        note = mark["note"]
        assert note.startswith("[Notice:") and note.endswith("]")
        assert "never by speaking faster" in note
        assert "Do not speak about the time" in note


@pytest.mark.parametrize("pacing", CLOCKS)
def test_the_phases_cover_the_whole_clock_in_order(pacing) -> None:
    phases = consultation_pacing_payload(pacing)["phases"]
    bounds = [p["until_seconds"] for p in phases]
    assert bounds == sorted(bounds)
    assert bounds[-1] == pacing.total_seconds
    assert all(p["label"] and not p["label"][0].isupper() for p in phases), "labels read mid-sentence"


def test_the_clock_survives_the_trip_to_the_worker() -> None:
    payload = consultation_pacing_payload(LONG)
    assert json.loads(json.dumps(payload)) == payload


@pytest.mark.parametrize("pacing", CLOCKS)
def test_a_mark_lands_early_enough_to_rescue_a_racing_consultation(pacing) -> None:
    """A real station reached its management plan at 3:22 and closed at 5:20.

    The first mark used to be at 40% of the clock, by which time everything had
    already gone wrong, and it only said what the 50% mark said moments later.
    """
    first = consultation_pacing_payload(pacing)["marks"][0]
    assert first["at_seconds"] <= pacing.total_seconds * 0.3
    assert "There is no credit for finishing early" in first["note"]


@pytest.mark.parametrize("pacing", CLOCKS)
def test_the_clock_speaks_to_a_doctor_who_is_ahead_as_well_as_behind(pacing) -> None:
    """Every note used to tell the doctor to trim, including the ones a fast doctor hits."""
    notes = [m["note"] for m in consultation_pacing_payload(pacing)["marks"]]
    assert all("or go further into" in n for n in notes), "the wrapper is two-directional"
    assert any("you are ahead: do not close" in n for n in notes)
