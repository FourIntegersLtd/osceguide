"""The model benchmark's arithmetic and its breach prefilter.

The replay itself needs a paid API and is not tested here. What is tested is
everything a reader will act on without re-deriving: the cost per consultation,
which decides whether a model is adopted, and the prefilter, which decides
whether a reply is flagged as leaving the role.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from model_bench import MEANINGFUL_BREACH_DELTA, PRICES, ROLES, Run, Turn, _verdict, prefilter, render_prompt, summarise  # noqa: E402
from osce_assessment.prompts._blocks import PATIENT_NEVER  # noqa: E402
from osce_assessment.prompts.debrief_prompt import TUTOR_NEVER  # noqa: E402

BENCH = Path(__file__).resolve().parents[1] / "scripts" / "bench"


def _turn(index: int = 0, *, out: int = 0, inp: int = 0, cached: int = 0, reply: str = "", said: str = "") -> Turn:
    return Turn(index=index, ttft_s=0.5, latency_s=1.0, output_tokens=out, input_tokens=inp,
                cached_tokens=cached, bait=None, said=said, reply=reply)


def test_cost_bills_cached_input_at_the_cached_rate() -> None:
    """Cached input is most of a voice consultation: the same system prompt, every turn."""
    run = Run(arm="gpt-4o-mini", role="patient", repeat=0,
              turns=[_turn(inp=1_000_000, cached=800_000, out=1_000_000)])
    rate_in, rate_cached, rate_out = PRICES["gpt-4o-mini"]
    assert run.cost_usd() == pytest.approx(0.2 * rate_in + 0.8 * rate_cached + rate_out)


def test_an_unpriced_model_costs_zero_rather_than_guessing() -> None:
    run = Run(arm="some-new-model", role="patient", repeat=0, turns=[_turn(inp=1000, out=1000)])
    assert run.cost_usd() == 0.0


def test_every_default_arm_has_a_price() -> None:
    """A missing price silently reports a model as free, which would decide a comparison wrongly."""
    for arm in ("gpt-4o-mini", "gpt-4o", "gpt-5.4-nano", "gpt-5.4-mini"):
        assert arm in PRICES


def test_the_prefilter_catches_a_patient_giving_management() -> None:
    run = Run(arm="x", role="patient", repeat=0, turns=[
        _turn(0, reply="I'd recommend getting it checked properly."),
        _turn(1, reply="Um... no, not really."),
    ])
    hits = prefilter(run, "patient")
    assert [h["turn"] for h in hits] == [0]
    assert hits[0]["kind"] == "gives management"


def test_the_prefilter_leaves_an_in_character_reply_alone() -> None:
    run = Run(arm="x", role="patient", repeat=0, turns=[
        _turn(0, reply="It comes on when I go up the stairs... eases off when I stop."),
        _turn(1, reply="I trust your judgment. I just hope to get some answers."),
    ])
    assert prefilter(run, "patient") == []


def test_the_prefilter_flags_a_no_that_reads_the_question_back() -> None:
    run = Run(arm="x", role="patient", repeat=0, turns=[
        _turn(0, reply="No, I haven't noticed any swelling in my ankles.", said="Any swelling in your ankles?"),
        _turn(1, reply="No, nothing like that.", said="Any swelling in your ankles?"),
        _turn(2, reply="It started about two weeks ago, mostly on the stairs.", said="When did the pain start?"),
    ])
    assert [(h["turn"], h["kind"]) for h in prefilter(run, "patient")] == [(0, "echoes the question")]


def test_a_no_at_the_length_limit_is_not_flagged_even_when_it_shares_a_word() -> None:
    """Eight words, no word of the question reused: a plain answer, not an echo."""
    run = Run(arm="x", role="patient", repeat=0, turns=[
        _turn(0, reply="No, it only comes on when I climb.", said="Any swelling in your ankles?"),
    ])
    assert prefilter(run, "patient") == []


def test_the_prefilter_is_patient_only() -> None:
    """A tutor legitimately says things a patient never would, so patterns would misfire."""
    run = Run(arm="x", role="tutor", repeat=0, turns=[_turn(0, reply="I'd recommend safety netting there.")])
    assert prefilter(run, "tutor") == []


def test_arms_are_ranked_by_breaches_then_cost() -> None:
    cheap_but_drifts = Run(arm="gpt-5.4-nano", role="patient", repeat=0, turns=[_turn(out=10)])
    cheap_but_drifts.judge = {"breaches": [{"turn": 1}, {"turn": 2}], "persona_consistency": 5, "conversational_quality": 5}
    holds_role = Run(arm="gpt-4o-mini", role="patient", repeat=0, turns=[_turn(out=100)])
    holds_role.judge = {"breaches": [], "persona_consistency": 4, "conversational_quality": 4}
    assert [row["arm"] for row in summarise([cheap_but_drifts, holds_role])] == ["gpt-4o-mini", "gpt-5.4-nano"]


def test_summary_averages_across_repeats() -> None:
    runs = []
    for repeat, breaches in enumerate(([], [{"turn": 1}])):
        run = Run(arm="gpt-4o-mini", role="patient", repeat=repeat, turns=[_turn(out=100)])
        run.judge = {"breaches": breaches, "persona_consistency": 4, "conversational_quality": 4}
        runs.append(run)
    row = summarise(runs)[0]
    assert row["consultations"] == 2
    assert row["judge_breaches"] == 0.5


SCRIPTS = sorted(p.stem for p in BENCH.glob("*.json"))


def test_there_is_a_script_for_every_live_persona() -> None:
    """Four personas ship, and orthopaedics inverts two of them, so five scripts."""
    roles = {json.loads((BENCH / f"{name}.json").read_text())["role"] for name in SCRIPTS}
    assert roles == set(ROLES)


@pytest.mark.parametrize("script_name", SCRIPTS)
def test_each_script_renders_the_prompt_its_role_needs(script_name) -> None:
    script = json.loads((BENCH / f"{script_name}.json").read_text())
    role = script["role"]
    instructions, reminder = render_prompt(role, script)
    assert instructions.startswith("<role>")
    assert ROLES[role]["reminder"] == reminder
    assert script["turns"], "a script with no turns measures nothing"


@pytest.mark.parametrize("script_name", SCRIPTS)
def test_every_script_carries_bait_because_drift_needs_inviting(script_name) -> None:
    """An unbaited script measures nothing: these models rarely leave the role unprompted."""
    script = json.loads((BENCH / f"{script_name}.json").read_text())
    baited = [t for t in script["turns"] if t.get("bait")]
    assert len(baited) >= 2, script_name
    assert all(t.get("why") for t in baited), "each bait turn says what it is testing"


def test_the_examiner_prompt_keeps_the_expected_answers_from_the_candidate() -> None:
    """The whole point of an examiner station: it holds the answers and must not give them out."""
    script = json.loads((BENCH / "candidate_ortho_clinical.json").read_text())
    instructions, _ = render_prompt("examiner", script)
    assert "hidden_until_asked" in instructions
    assert "never" in instructions.lower() and "expected answer" in instructions


@pytest.mark.parametrize(("role", "never"), [("patient", PATIENT_NEVER), ("tutor", TUTOR_NEVER)])
def test_the_judge_scores_against_what_the_model_was_actually_told(role, never) -> None:
    """A judge held to a stricter spec than the prompt invents breaches.

    The first run of this harness marked the tutor down for discussing the
    marking and for suggesting better phrasing, because the spec here had been
    written by hand and was stricter than the prompt. Deriving it from the
    prompt is what stops that recurring.
    """
    assert ROLES[role]["breaches"] is never


def test_a_patient_answering_teach_back_is_not_flagged() -> None:
    """Asked to say back what they would do, a patient should answer; refusing is the odd behaviour."""
    run = Run(arm="x", role="patient", repeat=0, turns=[
        Turn(index=0, ttft_s=0.5, latency_s=1.0, output_tokens=0, input_tokens=0, cached_tokens=0,
             bait=None, said="Could you summarise back what you'd do if it got worse?",
             reply="I'd call the surgery if it gets worse."),
    ])
    assert prefilter(run, "patient") == []


def test_a_patient_safety_netting_unprompted_is_still_flagged() -> None:
    run = Run(arm="x", role="patient", repeat=0, turns=[
        Turn(index=0, ttft_s=0.5, latency_s=1.0, output_tokens=0, input_tokens=0, cached_tokens=0,
             bait=None, said="Any nausea with it?",
             reply="No. You should come back if it gets worse, and call 999 for chest pain."),
    ])
    assert [h["kind"] for h in prefilter(run, "patient")] == ["safety-nets"]


def test_cheaper_and_no_worse_is_adopted() -> None:
    assert _verdict(fewer=0.0, saved=0.01) == "adopt"
    assert _verdict(fewer=2.0, saved=0.01) == "adopt"


def test_cheaper_but_worse_is_refused() -> None:
    assert _verdict(fewer=-2.0, saved=0.05) == "keep the baseline"


def test_dearer_but_meaningfully_better_is_surfaced_not_refused() -> None:
    """The examiner arm: one model broke its role five times a station, the other twice.

    A rule that only adopts when a candidate is also cheaper would have kept the
    worse model, which is the opposite of what the numbers say.
    """
    assert _verdict(fewer=3.3, saved=-0.004) == "better but dearer: worth it"


def test_dearer_and_barely_better_is_still_refused() -> None:
    """Inside the judge-noise floor, "better" is not a finding."""
    assert _verdict(fewer=MEANINGFUL_BREACH_DELTA - 0.1, saved=-0.01) == "keep the baseline"


def test_a_real_coverage_drop_outweighs_a_lower_breach_count() -> None:
    assert _verdict(fewer=1.0, saved=0.01, coverage_gap=-20.0) == "keep the baseline"
