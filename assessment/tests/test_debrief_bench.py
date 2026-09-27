"""The debrief benchmark's variant swapping, its talk arithmetic, its clock, and its fidelity to production.

The debriefs themselves need paid APIs and are not run here. What is tested is
what decides a variant's fate without a model: that a variant changes only the
block it names, that the talk numbers are right, and that the tutor hears the
same time notice the worker sends.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from debrief_bench import (  # noqa: E402
    BASELINE,
    TIME_NOTICE,
    VARIANTS,
    Turn,
    apply_variant,
    clock_status,
    conversation_text,
    load_scenarios,
    load_variant,
    marks_due,
    never_list,
    scenario_prompt,
    section_shares,
    seconds_at,
    talk_metrics,
    timed_reply,
)
from livekit_assessment_worker.notices import time_remaining_notice  # noqa: E402
from osce_assessment.prompts import DEBRIEF_PACING_BLOCK  # noqa: E402
from osce_assessment.prompts._blocks import role_lock  # noqa: E402

SCENARIOS = ["chest_pain", "new_type2_diabetes"]
VARIANT_NAMES = [BASELINE, *sorted(path.stem for path in VARIANTS.glob("*.txt"))]


def _turn(index: int, said: str, reply: str) -> Turn:
    """A debrief exchange: the trainee's line and the tutor's reply."""
    return Turn(index=index, ttft_s=0.5, latency_s=1.0, output_tokens=0, input_tokens=0,
                cached_tokens=0, bait=None, said=said, reply=reply)


def test_a_variant_replaces_only_the_block_it_names():
    prompt = "<role>\nold role\n</role>\n\n<speech>\nkeep me\n</speech>\n\n<how>\nold how\n</how>"
    swapped = apply_variant(prompt, {"role": "<role>\nnew role\n</role>"})
    assert swapped == "<role>\nnew role\n</role>\n\n<speech>\nkeep me\n</speech>\n\n<how>\nold how\n</how>"


def test_a_variant_naming_a_block_the_prompt_lacks_is_refused():
    with pytest.raises(ValueError, match="<portfolio> appears 0 times"):
        apply_variant("<role>\nx\n</role>", {"portfolio": "<portfolio>\ny\n</portfolio>"})


def test_a_replacement_containing_backslashes_is_inserted_verbatim():
    swapped = apply_variant("<role>\nx\n</role>", {"role": "<role>\nsay \\1 aloud\n</role>"})
    assert swapped == "<role>\nsay \\1 aloud\n</role>"


def test_the_never_list_is_read_from_the_role_block():
    prompt = role_lock(persona="the tutor", counterpart="the doctor", never=("invent facts", "say you are an AI"))
    assert never_list(prompt) == ["invent facts.", "say you are an AI."]


def test_talk_metrics_on_a_fixed_debrief():
    turns = [
        _turn(0, "It went okay I think", "Good. What felt hardest? And why?"),
        _turn(1, "The safety net", "Let's look at that together."),
    ]
    assert talk_metrics(turns) == {
        "tutor_share": 11 / 19,
        "mean_tutor_words": 5.5,
        "longest_tutor_words": 6.0,
        "questions_per_turn": 1.0,
        "stacked_question_turns": 0.5,
    }


def test_a_heading_the_judge_left_out_counts_as_missed():
    judged = {"sections": [{"title": "Explanation", "status": "built_together"},
                           {"title": "Follow-up", "status": "told"}]}
    shares = section_shares(judged, ["Explanation", "Follow-up", "Safety Netting", "Assessment"])
    assert shares == {"built_together": 0.25, "told": 0.25, "missed": 0.5}


def test_the_tutor_hears_the_notice_the_worker_sends():
    assert TIME_NOTICE == time_remaining_notice(60)


def test_a_variant_file_carries_its_own_greeting():
    variant = load_variant("walkthrough")
    assert variant.greeting.startswith("Hello doctor, I'm Athena")
    assert set(variant.blocks) == {"role", "how_the_debrief_goes"}


@pytest.mark.parametrize("scenario_name", SCENARIOS)
@pytest.mark.parametrize("variant_name", VARIANT_NAMES)
def test_every_variant_renders_on_every_scenario_with_the_case_intact(variant_name, scenario_name):
    scenario = load_scenarios([scenario_name])[scenario_name]
    prompt = scenario_prompt(scenario, load_variant(variant_name))
    assert prompt.startswith("<role>")
    assert prompt.count("<transcript>") == 1
    assert prompt.count("<management_plan>") == 1
    assert len(never_list(prompt)) == 4


def test_every_arm_carries_the_production_clock():
    scenario = load_scenarios(["chest_pain"])["chest_pain"]
    for name in (BASELINE, "walkthrough"):
        prompt = scenario_prompt(scenario, load_variant(name))
        assert prompt.count(DEBRIEF_PACING_BLOCK) == 1, name


def test_the_marks_pass_once_each_at_their_exchanges():
    fired: dict[int, int] = {}
    sent = 0
    for index in range(18):
        due = marks_due(index, sent)
        if due:
            fired[index] = len(due)
            sent += len(due)
    assert fired == {4: 1, 8: 1, 13: 1, 16: 1}
    assert marks_due(4, 0)[0].startswith("[Notice: About 2 min 30 sec have gone, a quarter of this debrief")
    assert marks_due(4, 0)[0].endswith("Do not speak about the time, and do not mention this note.]")


def test_the_client_warning_lands_one_minute_before_the_end():
    assert seconds_at(14) == 540


def test_check_time_answers_in_the_doctor_clock_wording():
    assert clock_status(seconds_at(8)) == (
        "About 5 min 9 sec gone of 10 min; about 4 min 51 sec left. You should be in: working through the "
        "management plan together, until about 8 min. If you are already past that, you are ahead of the clock: "
        "go further into what you have rather than closing early."
    )
    assert clock_status(620) == (
        "About 10 min 20 sec gone of 10 min. You are past the time set aside: finish the point you are on "
        "and close. Do not start anything new."
    )


def test_the_judge_reads_pushed_notices_before_the_line_and_a_clock_check_after_it():
    notices = [{"before": 1, "kind": "mark", "text": "[Notice: half]"},
               {"before": 1, "kind": "check_time", "text": "About 5 min gone"}]
    text = conversation_text("Hello", [_turn(0, "Hi", "How was it?"), _turn(1, "Fine", "Let's look at the plan.")],
                             notices)
    assert text == (
        "[turn 0] TUTOR: Hello\n"
        "[turn 1] TRAINEE: Hi\n[turn 1] TUTOR: How was it?\n"
        "(the tutor is told privately: [Notice: half])\n"
        "[turn 2] TRAINEE: Fine\n"
        "(the tutor checks the time privately, and reads: About 5 min gone)\n"
        "[turn 2] TUTOR: Let's look at the plan."
    )


class _ToolCall:
    """The part of an OpenAI tool call the bench reads."""

    id = "call_1"

    def model_dump(self) -> dict[str, Any]:
        """The call as it goes back into the history."""
        return {"id": self.id, "type": "function", "function": {"name": "check_time", "arguments": "{}"}}


class _ClockCheckingTutor:
    """A tutor that checks the clock once, then speaks; records every request it was sent."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        """Answer with a tool call the first time and words the second."""
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        checking = len(self.requests) == 1
        message = SimpleNamespace(content=None if checking else " Let's go to the safety net. ",
                                  tool_calls=[_ToolCall()] if checking else None)
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=10,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=40))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def test_a_clock_check_is_answered_from_the_simulated_clock_and_kept_in_the_history():
    tutor = _ClockCheckingTutor()
    history: list[dict[str, Any]] = [{"role": "user", "content": "What next?"}]
    notices: list[dict[str, Any]] = []
    turn = timed_reply(tutor, instructions="be a tutor", history=history, index=8, said="What next?",
                       notices=notices)
    assert turn.reply == "Let's go to the safety net."
    assert (turn.input_tokens, turn.cached_tokens, turn.output_tokens) == (200, 80, 20)
    assert history[-1] == {"role": "tool", "tool_call_id": "call_1", "content": clock_status(seconds_at(8))}
    assert notices == [{"before": 8, "kind": "check_time", "text": clock_status(seconds_at(8))}]
    assert tutor.requests[1]["messages"][-1]["role"] == "tool"
