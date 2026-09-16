"""The clock, and the one thing that must never drift: prompt text versus schedule.

Both the phase budgets the model reads and the marks the worker fires come from
one table. If someone edits a duration and only half of it moves, the doctor is
told it has five and a half minutes for history while the notice telling it to
stop arrives at four. The parse-it-back test below is what catches that.
"""

from __future__ import annotations

import json
import re

import pytest

from osce_assessment.prompts import AthenaDoctorFormatter, consultation_pacing_payload, pacing_for_framework
from osce_assessment.prompts.consultation_pacing import PACING_BY_FRAMEWORK_ID, human_duration

FRAMEWORKS = sorted(PACING_BY_FRAMEWORK_ID)


@pytest.mark.parametrize(("framework_id", "total"), [("sca-rcgp-v1", 720), ("plab2-gmc-v1", 480), ("casc-rcpsych-v1", 480), ("ortho-frcs-v1", 600)])
def test_each_exam_gets_the_station_length_the_product_already_uses(framework_id, total) -> None:
    pacing = pacing_for_framework(framework_id)
    assert pacing.total_seconds == total
    assert pacing.history_seconds * 2 == total, "history is half the station"


def test_an_unknown_exam_gets_the_longest_clock_rather_than_the_shortest() -> None:
    """Too much time reads as unhurried; too little reads as the rush this exists to fix."""
    assert pacing_for_framework("something-else") == pacing_for_framework("sca-rcgp-v1")
    assert pacing_for_framework(None) == pacing_for_framework("sca-rcgp-v1")
    assert pacing_for_framework(" SCA-RCGP-V1 ") == pacing_for_framework("sca-rcgp-v1")


@pytest.mark.parametrize("framework_id", FRAMEWORKS)
def test_the_phase_budgets_in_the_prompt_are_the_ones_the_clock_runs_on(framework_id) -> None:
    """The anti-drift test: read the minutes back out of the rendered prompt."""
    pacing = pacing_for_framework(framework_id)
    prompt = AthenaDoctorFormatter.create_prompt("Hypothyroidism", {}, {"explanation": "x"}, pacing=pacing)
    budgets = dict(re.findall(r"^PHASE (\d) — [A-Z4 ]+\(~([\d.]+ (?:sec|min))", prompt, flags=re.MULTILINE))
    assert budgets["1"] == human_duration(pacing.introduction_seconds)
    assert budgets["2"] == human_duration(pacing.history_talk_seconds)
    assert budgets["3"] == human_duration(pacing.management_seconds)
    assert budgets["4"] == human_duration(pacing.safety_net_seconds)
    assert human_duration(pacing.total_seconds) in prompt, "and the whole length is stated once"


def test_a_shorter_exam_changes_the_budgets_and_nothing_else() -> None:
    args = ("Hypothyroidism", {}, {"explanation": "x"})
    sca = AthenaDoctorFormatter.create_prompt(*args, pacing=pacing_for_framework("sca-rcgp-v1"))
    plab = AthenaDoctorFormatter.create_prompt(*args, pacing=pacing_for_framework("plab2-gmc-v1"))
    differing = [a for a, b in zip(sca.splitlines(), plab.splitlines()) if a != b]
    assert differing, "the budgets do move"
    assert all("PHASE" in line or "This consultation is about" in line for line in differing)


def test_the_doctor_defaults_to_a_full_length_consultation() -> None:
    """Three positional args is how the bench and most callers still invoke it."""
    assert AthenaDoctorFormatter.create_prompt("Hypothyroidism", {}, {}) == AthenaDoctorFormatter.create_prompt(
        "Hypothyroidism", {}, {}, pacing=pacing_for_framework("sca-rcgp-v1")
    )


@pytest.mark.parametrize("framework_id", FRAMEWORKS)
def test_the_marks_walk_forward_and_stop_at_the_end(framework_id) -> None:
    marks = [m["at_seconds"] for m in consultation_pacing_payload(framework_id)["marks"]]
    total = pacing_for_framework(framework_id).total_seconds
    assert marks == sorted(marks) and len(set(marks)) == len(marks)
    assert marks[0] > 0 and marks[-1] == total, "the last word arrives at time, not after it"


@pytest.mark.parametrize("framework_id", FRAMEWORKS)
def test_every_note_says_to_drop_things_rather_than_hurry(framework_id) -> None:
    """A clock the model reads as permission to talk faster would be worse than none."""
    for mark in consultation_pacing_payload(framework_id)["marks"]:
        note = mark["note"]
        assert note.startswith("[Notice:") and note.endswith("]")
        assert "never by speaking faster" in note
        assert "Do not speak about the time" in note


@pytest.mark.parametrize("framework_id", FRAMEWORKS)
def test_the_phases_cover_the_whole_clock_in_order(framework_id) -> None:
    phases = consultation_pacing_payload(framework_id)["phases"]
    bounds = [p["until_seconds"] for p in phases]
    assert bounds == sorted(bounds)
    assert bounds[-1] == pacing_for_framework(framework_id).total_seconds
    assert all(p["label"] and not p["label"][0].isupper() for p in phases), "labels read mid-sentence"


def test_the_clock_survives_the_trip_to_the_worker() -> None:
    payload = consultation_pacing_payload("sca-rcgp-v1")
    assert json.loads(json.dumps(payload)) == payload


@pytest.mark.parametrize("framework_id", FRAMEWORKS)
def test_a_mark_lands_early_enough_to_rescue_a_racing_consultation(framework_id) -> None:
    """A real station reached its management plan at 3:22 and closed at 5:20.

    The first mark used to be at 40% of the clock, by which time everything had
    already gone wrong, and it only said what the 50% mark said moments later.
    """
    pacing = pacing_for_framework(framework_id)
    first = consultation_pacing_payload(framework_id)["marks"][0]
    assert first["at_seconds"] <= pacing.total_seconds * 0.3
    assert "There is no credit for finishing early" in first["note"]


@pytest.mark.parametrize("framework_id", FRAMEWORKS)
def test_the_clock_speaks_to_a_doctor_who_is_ahead_as_well_as_behind(framework_id) -> None:
    """Every note used to tell the doctor to trim, including the ones a fast doctor hits."""
    notes = [m["note"] for m in consultation_pacing_payload(framework_id)["marks"]]
    assert all("or go further into" in n for n in notes), "the wrapper is two-directional"
    assert any("you are ahead: do not close" in n for n in notes)
