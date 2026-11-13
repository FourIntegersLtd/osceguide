"""Which of an exam's own words the non-verbal cues are shown under."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.features.attempts.domain_nonverbal import build_facts
from app.features.attempts.domain_nonverbal_lingo import lingo_for
from app.features.rubrics import domain as rubric_domain

SEED = Path(__file__).parents[2] / "seeds" / "platform-starter.json"
DEFAULT = "Non-verbal communication"


def _framework(code: str) -> dict:
    """The framework an attempt on this shipped exam freezes, built from the seeded rubric."""
    entry = next(e for e in json.loads(SEED.read_text())["exams"] if e["code"] == code)
    return rubric_domain.framework_payload(
        framework_id="f",
        label=entry["rubric"]["title"],
        version="1",
        structure=rubric_domain.parse_structure(entry["rubric"]["structure"]),
        system_prompt="x",
    )


def test_none_and_empty_frameworks_give_the_defaults():
    expected = {
        "heading": DEFAULT,
        "attention_label": DEFAULT,
        "listening_label": DEFAULT,
        "rapport_label": DEFAULT,
    }
    assert lingo_for(None) == expected
    assert lingo_for({"domains": [{"id": "a", "label": "Knowledge"}], "competencies": []}) == expected


def test_competency_beats_domain_and_stems_are_ordered():
    framework = {
        "domains": [{"id": "d", "label": "Interpersonal skills"}],
        "competencies": [
            {"id": "c1", "label": "Communicates clearly", "domain_id": "d"},
            {"id": "c2", "label": "Stays attentive", "domain_id": "d"},
        ],
    }
    result = lingo_for(framework)
    # "responsive"/"attentive" outrank "communicat" for attention, so c2 wins over c1.
    assert result["attention_label"] == "Stays attentive"
    assert result["heading"] == "Interpersonal skills"
    assert result["rapport_label"] == "Communicates clearly"


@pytest.mark.parametrize("code", ["sca", "plab", "ortho", "casc"])
def test_shipped_exam_wording(code):
    assert lingo_for(_framework(code)) == EXPECTED[code]


EXPECTED: dict[str, dict[str, str]] = {
    "sca": {
        "heading": "Global skills",
        "attention_label": "Remains responsive to patient",
        "listening_label": "Remains responsive to patient",
        "rapport_label": "Generates rapport",
    },
    "plab": {
        "heading": "Interpersonal skills",
        "attention_label": "Rapport",
        "listening_label": "Listening",
        "rapport_label": "Rapport",
    },
    "casc": {
        "heading": "Communication",
        "attention_label": "Communication",
        "listening_label": "Listening skills",
        "rapport_label": "Communication",
    },
    "ortho": {
        "heading": "Clinical skills",
        "attention_label": "Communication information gathering",
        "listening_label": "Communication information gathering",
        "rapport_label": "Communication information gathering",
    },
}


# --- build_facts ---------------------------------------------------------------------------------

T0 = datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)
T0_MS = int(T0.timestamp() * 1000)


def _series(count, *, away=(), nods=(), nofaces=(), smiles=(), offset_ms=0):
    """`count` one-second samples; sample i ends i seconds after T0 (shifted by offset_ms)."""
    return [
        {
            "at_ms": T0_MS + i * 1000 + offset_ms,
            "face": i not in nofaces,
            "away": i in away,
            "yaw": 0,
            "pitch": 0,
            "smile": 80 if i in smiles else 0,
            "nod": i in nods,
        }
        for i in range(count)
    ]


def _turn(seq, role, end_s, message="words"):
    """A turn stamped when it ended, `end_s` seconds after T0 (how the worker stamps it)."""
    return (seq, role, message, T0 + timedelta(seconds=end_s))


TURNS = [
    _turn(0, "user", 10, "Hello, I am Dr Khan"),
    _turn(1, "assistant", 30, "My chest has been tight"),
    _turn(2, "user", 60, "Tell me more about it"),
]


def test_under_sixty_seconds_is_insufficient():
    assert build_facts([(0, _series(59))], TURNS)["insufficient"] is True
    assert build_facts([(0, _series(60))], TURNS)["insufficient"] is False


def test_a_face_in_under_sixty_percent_of_seconds_is_insufficient():
    facts = build_facts([(0, _series(100, nofaces=range(41)))], TURNS)
    assert (facts["seconds_total"], facts["seconds_face"], facts["insufficient"]) == (100, 59, True)


def test_facing_percent_nods_and_opening_smile():
    samples = _series(100, nofaces=range(80, 100), away=range(20, 40), nods=(5, 6, 50), smiles=(29,))
    facts = build_facts([(0, samples)], TURNS)
    assert (facts["seconds_face"], facts["facing_percent"], facts["nods_total"]) == (80, 75, 3)
    assert facts["smiled_in_opening"] is True
    assert build_facts([(0, _series(100, smiles=(30,)))], TURNS)["smiled_in_opening"] is False


def test_overlapping_batches_count_a_second_once():
    facts = build_facts([(5, _series(40)), (5, _series(40, offset_ms=20_000)[:40])], TURNS)
    assert facts["seconds_total"] == 60


def test_an_away_span_is_attached_to_the_turn_it_started_in():
    facts = build_facts([(0, _series(70, away=range(20, 28)))], TURNS)
    assert facts["away_spans"] == [
        {
            "start_seconds": 20,
            "duration_seconds": 8,
            "seq": 1,
            "role": "assistant",
            "quote": "My chest has been tight",
        }
    ]
    assert facts["notable_turns"] == [
        {
            "seq": 1,
            "start_seconds": 20,
            "quote": "My chest has been tight",
            "note": "looked away for 8 of 20 seconds while listening, no nods",
        }
    ]


def test_skew_correction_moves_a_span_onto_the_right_turn():
    """The browser clock ran 15 s behind the server's, so the same span belongs to turn 1, not turn 0."""
    behind = _series(70, away=range(20, 28), offset_ms=-15_000)
    assert build_facts([(15_000, behind)], TURNS)["away_spans"][0]["seq"] == 1
    assert build_facts([(0, behind)], TURNS)["away_spans"][0]["seq"] == 0


def test_the_median_skew_is_used_for_every_batch():
    first, second = _series(35), _series(35, offset_ms=35_000)
    facts = build_facts([(15_000, first), (15_000, second), (99_999, [])], TURNS)
    assert facts["seconds_total"] == 70 and facts["insufficient"] is False


def test_a_gap_of_two_seconds_does_not_break_a_span_but_three_does():
    joined = build_facts([(0, _series(70, away=(20, 21, 24, 25, 26)))], TURNS)
    assert [(s["start_seconds"], s["duration_seconds"]) for s in joined["away_spans"]] == [(20, 7)]
    split = build_facts([(0, _series(70, away=(20, 21, 25, 26, 27)))], TURNS)
    assert split["away_spans"] == []


def test_nods_are_counted_for_the_patients_turns_only():
    facts = build_facts([(0, _series(70, nods=(15, 16, 40)))], TURNS)
    assert (facts["nods_total"], facts["nods_while_patient_spoke"]) == (3, 2)


def test_a_patient_turn_with_no_nods_and_three_seconds_away_is_notable():
    """The patient's window is when the clinician was listening."""
    facts = build_facts([(0, _series(61, away=(15, 16, 17)))], TURNS)
    assert facts["notable_turns"] == [
        {
            "seq": 1,
            "start_seconds": 15,
            "quote": "My chest has been tight",
            "note": "looked away for 3 of 20 seconds while listening, no nods",
        }
    ]
    with_nod = build_facts([(0, _series(61, away=(15, 16, 17), nods=(20,)))], TURNS)
    assert with_nod["notable_turns"] == []


def test_a_candidate_turn_after_the_patient_is_not_notable_for_three_or_four_seconds_away():
    """While the clinician is talking, nodding means nothing; only the five-second rule applies."""
    for away in ((31, 32, 33), (31, 32, 33, 34)):
        assert build_facts([(0, _series(61, away=away))], TURNS)["notable_turns"] == []
    five = build_facts([(0, _series(61, away=range(31, 36)))], TURNS)
    assert five["notable_turns"][0]["note"] == "looked away for 5 of 30 seconds while speaking"


def test_a_first_turn_that_is_the_patient_is_notable_when_listened_to_without_nodding():
    turns = [_turn(0, "assistant", 30, "Good morning, doctor"), _turn(1, "user", 60, "Hello")]
    facts = build_facts([(0, _series(61, away=(10, 11, 12)))], turns)
    assert [t["seq"] for t in facts["notable_turns"]] == [0]


def test_a_quote_is_cut_at_160_characters():
    turns = [_turn(0, "user", 70, "x" * 300)]
    facts = build_facts([(0, _series(70, away=range(10, 16)))], turns)
    assert facts["notable_turns"][0]["quote"] == "x" * 160
