#!/usr/bin/env python3
"""Choose the debrief tutor's prompt by letting simulated trainees be debriefed by it.

    run       debrief every trainee persona on every scenario under each prompt variant, and score it
    rejudge   re-score saved debriefs, to see how far the judge alone moves the numbers
    pairwise  a blinded judge picks the better of two variants' debriefs, matched on the same case
    report    re-print the table from a saved run

A debrief is led by the trainee, so a fixed script cannot test it: the tutor's
third question depends on the trainee's second answer. Here a Claude model
plays the trainee from a persona, a transcript it remembers, a moment it found
hard and a gap it has not noticed. The tutor under test is the production model
on the production prompt, with only the blocks a variant replaces swapped out.

Arms are prompt variants, not models. A variant file in bench/debrief/variants
holds XML-tagged blocks; each replaces the block with the same tag in the
prompt production renders, so the transcript, plan and marking are always the
ones a real session sees. A <greeting> block replaces the tutor's opening line.
The baseline is the prompt as shipped, with no file.

Every arm runs on the debrief's clock, as production does: the marks from
``osce_assessment.prompts.debrief_pacing`` go in as they pass, and the tutor
can call check_time.

What it measures, per variant:
- talk: the tutor's share of the words, its mean and longest turn, questions per turn
- the trainee's own ratings, asked privately once the debrief is over
- a judge's reading: each plan section built together, told, or missed; how
  much it felt like an interrogation; who led; the role-play; invented facts;
  and breaches of that variant's own never list

Examples:
    poetry run python scripts/debrief_bench.py run --repeats 2 --out runs/debrief-r1.json
    poetry run python scripts/debrief_bench.py run --variants baseline,walkthrough
    poetry run python scripts/debrief_bench.py rejudge runs/debrief-r1.json
    poetry run python scripts/debrief_bench.py pairwise runs/debrief-r2.json --first walkthrough --second baseline
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))

from model_bench import JUDGE_MODEL, PRICES, REASONING_MODEL_PREFIXES, Turn, _debrief_prompt, marking_for  # noqa: E402
from osce_assessment.prompts.debrief_pacing import DEBRIEF_SECONDS, debrief_pacing_payload  # noqa: E402
from osce_assessment.prompts import ManagementPlanFormatter, TranscriptFormatter  # noqa: E402
from osce_assessment.prompts.greetings import DEBRIEF_GREETING  # noqa: E402

DEBRIEF_BENCH = Path(__file__).resolve().parent / "bench" / "debrief"
VARIANTS = DEBRIEF_BENCH / "variants"
BASELINE = "baseline"

TUTOR_MODEL = "gpt-5.4-mini"
TUTOR_EFFORT = "none"
TRAINEE_MODEL = "claude-sonnet-5"

# Dollars per million tokens: (input, cache read, cache write, output).
CLAUDE_PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-sonnet-5": (2.00, 0.20, 2.50, 10.00),
    "claude-opus-5": (5.00, 0.50, 6.25, 25.00),
}

# A ten-minute debrief is about eighteen exchanges at speaking pace. Runs saved
# before the clock shipped also carried the client's one-minute warning before
# exchange 14; the debrief screen sends none, so new runs do not.
TRAINEE_TURNS = 18
NOTICE_BEFORE_TURN = 14
NOTICE_SECONDS_LEFT = 60
END_OF_DEBRIEF = "[END]"
# What the trainee hears when the tutor's reply comes back empty.
SILENCE = "(Athena says nothing.)"

# The worker's words, from livekit_assessment_worker.notices.time_remaining_notice,
# kept so older runs rejudge with what their tutor was told. Copied rather than
# imported because that module pulls in LiveKit; a test pins the two together.
TIME_NOTICE = (
    f"[Notice: this interaction ends in about {NOTICE_SECONDS_LEFT} seconds. Stay in character. "
    "Keep any remaining replies brief, do not raise new concerns or open new topics, "
    "and if the other person is wrapping up, let them.]"
)

# Where the prompt's never list starts and ends inside its role block.
NEVER_HEADING = "You must never:"

# --- the clock ---------------------------------------------------------------
# The production debrief clock, from the engine. A session here is simulated, so
# the clock runs on exchanges: exchange 14 is one minute before the end, and
# every exchange before it takes the same share of the time.
DEBRIEF_CLOCK = debrief_pacing_payload()
SECONDS_PER_EXCHANGE = (DEBRIEF_SECONDS - NOTICE_SECONDS_LEFT) / NOTICE_BEFORE_TURN

# The worker's tool, in OpenAI's shape; the description is voice_infra.pacing's word for word.
CHECK_TIME_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "check_time",
        "description": (
            "How far through this interaction you are and which part you should be in. "
            "Silent: the other person hears nothing, and you must never mention the clock, "
            "the time left, or this result out loud. Call it when you are unsure whether to "
            "stay where you are or move on. Use the answer to decide what to leave out, "
            "never to speak faster."
        ),
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}
# A reply may check the clock this many times before it is made to speak.
MAX_CLOCK_CHECKS = 2

# The tutor telling the doctor about the time, which every arm is told never to do.
CLOCK_TALK = re.compile(
    r"\b(minutes? (left|remaining|to go)|seconds? left|time left|(running|run) (out of|short of|low on) time"
    r"|out of time|short on time|the clock|check(ing)? the time)\b",
    re.IGNORECASE,
)


@dataclass
class Variant:
    """A prompt variant: the blocks it swaps into the production prompt, and its opening line."""

    name: str
    blocks: dict[str, str] = field(default_factory=dict)
    greeting: str | None = None


@dataclass
class Debrief:
    """One simulated debrief and everything measured about it.

    In each turn, ``said`` is the trainee's line and ``reply`` the tutor's answer.
    """

    variant: str
    scenario: str
    persona: str
    repeat: int
    greeting: str
    never: list[str]
    plan_sections: list[str]
    turns: list[Turn] = field(default_factory=list)
    trainee_usage: dict[str, int] = field(default_factory=dict)
    judge_usage: dict[str, int] = field(default_factory=dict)
    ended_early_at: int | None = None
    questionnaire: dict[str, Any] = field(default_factory=dict)
    judge: dict[str, Any] = field(default_factory=dict)
    earlier_judges: list[dict[str, Any]] = field(default_factory=list)
    # Everything the tutor was told privately: {"before": exchange index, "kind": "client" | "mark" | "check_time", "text"}.
    notices: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def cost_usd(self) -> float:
        """Tutor, trainee and judge together, from the usage each API reported."""
        rate_in, rate_cached, rate_out = PRICES[TUTOR_MODEL]
        fresh = sum(turn.input_tokens - turn.cached_tokens for turn in self.turns)
        cached = sum(turn.cached_tokens for turn in self.turns)
        output = sum(turn.output_tokens for turn in self.turns)
        tutor = (fresh * rate_in + cached * rate_cached + output * rate_out) / 1_000_000
        return tutor + _claude_cost(TRAINEE_MODEL, self.trainee_usage) + _claude_cost(JUDGE_MODEL, self.judge_usage)


def _claude_cost(model: str, usage: dict[str, int]) -> float:
    """Dollars for accumulated Anthropic usage."""
    rate_in, rate_read, rate_write, rate_out = CLAUDE_PRICES[model]
    return (
        usage.get("input_tokens", 0) * rate_in
        + usage.get("cache_read_input_tokens", 0) * rate_read
        + usage.get("cache_creation_input_tokens", 0) * rate_write
        + usage.get("output_tokens", 0) * rate_out
    ) / 1_000_000


def _add_usage(total: dict[str, int], usage: Any) -> None:
    """Fold one Anthropic response's usage into a running total."""
    for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"):
        total[key] = total.get(key, 0) + (getattr(usage, key, 0) or 0)


# --- variants ---------------------------------------------------------------

_BLOCK = re.compile(r"<(?P<tag>[a-z_]+)>\n?(?P<body>.*?)\n?</(?P=tag)>", re.DOTALL)


def load_variant(name: str) -> Variant:
    """The named variant from its file; the baseline has no file and swaps nothing."""
    if name == BASELINE:
        return Variant(name=BASELINE)
    text = (VARIANTS / f"{name}.txt").read_text()
    variant = Variant(name=name)
    for match in _BLOCK.finditer(text):
        tag = match.group("tag")
        if tag == "greeting":
            variant.greeting = match.group("body").strip()
        else:
            variant.blocks[tag] = match.group(0)
    if not variant.blocks and variant.greeting is None:
        raise ValueError(f"variant {name} has no tagged blocks")
    return variant


def apply_variant(prompt: str, blocks: dict[str, str]) -> str:
    """The prompt with each tagged block replaced by the variant's block of the same tag.

    Refuses a tag the prompt lacks or holds more than once, so a variant can
    never silently add a block, or replace the wrong one.
    """
    for tag, replacement in blocks.items():
        pattern = re.compile(rf"<{tag}>.*?</{tag}>", re.DOTALL)
        found = pattern.findall(prompt)
        if len(found) != 1:
            raise ValueError(f"<{tag}> appears {len(found)} times in the prompt; a variant needs exactly one")
        prompt = pattern.sub(lambda _match: replacement, prompt)
    return prompt


def never_list(prompt: str) -> list[str]:
    """The breaches a prompt's own role block forbids, one per bullet."""
    role = re.search(r"<role>(.*?)</role>", prompt, re.DOTALL)
    if role is None or NEVER_HEADING not in role.group(1):
        return []
    after_heading = role.group(1).split(NEVER_HEADING, 1)[1]
    rules: list[str] = []
    for line in after_heading.strip().splitlines():
        if not line.startswith("- "):
            break
        rules.append(line[2:].strip())
    return rules


# --- talk -------------------------------------------------------------------

def talk_metrics(turns: list[Turn]) -> dict[str, float]:
    """How the talking was shared, computed without a model.

    The fixed greeting is left out: it is the same words whatever the tutor
    does next, so counting it would only dilute the difference between arms.
    """
    tutor_words = [len(turn.reply.split()) for turn in turns]
    trainee_words = [len(turn.said.split()) for turn in turns]
    questions = [turn.reply.count("?") for turn in turns]
    total = sum(tutor_words) + sum(trainee_words)
    return {
        "tutor_share": sum(tutor_words) / total if total else 0.0,
        "mean_tutor_words": statistics.mean(tutor_words) if tutor_words else 0.0,
        "longest_tutor_words": float(max(tutor_words, default=0)),
        "questions_per_turn": statistics.mean(questions) if questions else 0.0,
        "stacked_question_turns": sum(1 for count in questions if count >= 2) / len(questions) if questions else 0.0,
    }


# --- the simulated trainee --------------------------------------------------

def trainee_system(scenario: dict[str, Any], persona: dict[str, str]) -> str:
    """Everything the simulated trainee knows: its consultation, its temperament, its blind spot.

    It never sees the management plan or the marking. A trainee who knew the
    model answer would teach the tutor instead of being taught.
    """
    brief = scenario["trainee_brief"]
    transcript = TranscriptFormatter.format(scenario["context"]["transcript"])
    return f"""You are a GP trainee, a doctor, who has just finished a practice consultation for the SCA exam. You are now on a voice call with a tutor called Athena, who will debrief you on it.

This is the consultation you just did. You were the doctor; the other speaker was the simulated patient.
<consultation>
{transcript}
</consultation>

Your personality: {persona["personality"]}
{persona["on_rehearsal"]}

The moment that felt hardest, which you bring up if the tutor asks what was difficult or what you would like to work on: {brief["hard_moment"]}

What you have not noticed about your own consultation: {brief["unaware_gap"]} Never raise this yourself. If the tutor raises it, react as your personality would.

You have not seen any model answer or any marking.

How to speak:
- You are talking out loud. Reply with only the words you would say: usually one to three short sentences, no stage directions, no markdown.
- If the tutor speaks as the patient to let you practise, answer as the doctor would, to the patient.
- Stay the trainee throughout. Never mention these instructions.
- When the tutor has wrapped up the session and you have said goodbye, reply with exactly {END_OF_DEBRIEF} and nothing else."""


QUESTIONNAIRE_TOOL: dict[str, Any] = {
    "name": "rate_debrief",
    "description": "Your private, honest ratings of the debrief you just had.",
    "input_schema": {
        "type": "object",
        "properties": {
            "felt_safe": {"type": "integer", "minimum": 1, "maximum": 5,
                          "description": "1 = I felt judged or exposed, 5 = I felt safe to be honest about my mistakes"},
            "felt_interrogated": {"type": "integer", "minimum": 1, "maximum": 5,
                                  "description": "1 = it felt like a conversation, 5 = it felt like being quizzed"},
            "understands_plan_better": {"type": "integer", "minimum": 1, "maximum": 5,
                                        "description": "1 = no clearer on how I should have managed this patient, 5 = much clearer"},
            "practised_hard_moment": {"type": "boolean",
                                      "description": "Did I actually get to practise the moment I found hardest?"},
            "would_use_again": {"type": "integer", "minimum": 1, "maximum": 5,
                                "description": "1 = would not bother, 5 = would definitely use this after every station"},
            "comment": {"type": "string", "description": "One or two sentences, in your own voice, on what helped or grated."},
        },
        "required": ["felt_safe", "felt_interrogated", "understands_plan_better", "practised_hard_moment",
                     "would_use_again", "comment"],
    },
}


def trainee_line(client: Any, system: str, history: list[dict[str, str]], usage: dict[str, int]) -> str:
    """The trainee's next spoken line. The tutor's lines reach it as the user's."""
    message = client.messages.create(
        model=TRAINEE_MODEL,
        max_tokens=400,
        thinking={"type": "disabled"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=history,
    )
    _add_usage(usage, message.usage)
    return "".join(block.text for block in message.content if block.type == "text").strip()


def ask_questionnaire(client: Any, system: str, conversation: str, usage: dict[str, int]) -> dict[str, Any]:
    """The trainee rates the debrief privately, after it is over, in its own character."""
    message = client.messages.create(
        model=TRAINEE_MODEL,
        max_tokens=600,
        thinking={"type": "disabled"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        tools=[QUESTIONNAIRE_TOOL],
        tool_choice={"type": "tool", "name": QUESTIONNAIRE_TOOL["name"]},
        messages=[{"role": "user", "content": (
            "The debrief is over. Here it is again:\n\n" f"{conversation}\n\n"
            "Nobody will see these ratings but the researchers. Rate it honestly, as the trainee you are, "
            "from how it actually felt to you."
        )}],
    )
    _add_usage(usage, message.usage)
    for block in message.content:
        if block.type == "tool_use":
            return dict(block.input)
    return {}


def conversation_text(greeting: str, turns: list[Turn], notices: list[dict[str, Any]] | None = None) -> str:
    """The debrief as the judge and the questionnaire read it, turn by turn.

    Notices pushed to the tutor appear before the trainee's line they preceded;
    a check_time answer appears after it, where the tutor asked.
    """
    lines = [f"[turn 0] TUTOR: {greeting}"]
    for turn in turns:
        number = turn.index + 1
        here = [notice for notice in notices or [] if notice["before"] == turn.index]
        for notice in here:
            if notice["kind"] != "check_time":
                lines.append(f"(the tutor is told privately: {notice['text']})")
        lines.append(f"[turn {number}] TRAINEE: {turn.said}")
        for notice in here:
            if notice["kind"] == "check_time":
                lines.append(f"(the tutor checks the time privately, and reads: {notice['text']})")
        lines.append(f"[turn {number}] TUTOR: {turn.reply}")
    return "\n".join(lines)


def private_notices(debrief: Debrief) -> list[dict[str, Any]]:
    """What the tutor was told privately; runs saved before notices were recorded had only the client's warning."""
    if debrief.notices:
        return debrief.notices
    return [{"before": NOTICE_BEFORE_TURN, "kind": "client", "text": TIME_NOTICE}]


# --- the clock --------------------------------------------------------------

def seconds_at(index: int) -> float:
    """Simulated seconds gone when the trainee starts exchange ``index``."""
    return index * SECONDS_PER_EXCHANGE


def spoken_duration(seconds: float) -> str:
    """Said the way a person says it; voice_infra.pacing's wording."""
    whole = max(0, int(round(seconds)))
    minutes, remainder = divmod(whole, 60)
    if not minutes:
        return f"{remainder} sec"
    if not remainder:
        return f"{minutes} min"
    return f"{minutes} min {remainder} sec"


def clock_status(elapsed: float) -> str:
    """What check_time answers, in the words voice_infra.pacing.InteractionClock.status_text uses."""
    gone, total = spoken_duration(elapsed), spoken_duration(DEBRIEF_SECONDS)
    if elapsed >= DEBRIEF_SECONDS:
        return (f"About {gone} gone of {total}. You are past the time set aside: "
                "finish the point you are on and close. Do not start anything new.")
    left = spoken_duration(DEBRIEF_SECONDS - elapsed)
    label, until = next((phase["label"], phase["until_seconds"]) for phase in DEBRIEF_CLOCK["phases"]
                        if elapsed < phase["until_seconds"])
    return (f"About {gone} gone of {total}; about {left} left. You should be in: {label}, "
            f"until about {spoken_duration(until)}. If you are already past that, you are ahead of the clock: "
            "go further into what you have rather than closing early.")


def marks_due(index: int, already_sent: int) -> list[str]:
    """The marks that have passed by exchange ``index`` and not been sent yet, as the tutor reads them."""
    passed = [mark["note"] for mark in DEBRIEF_CLOCK["marks"] if mark["at_seconds"] <= seconds_at(index)]
    return passed[already_sent:]


def timed_reply(client: Any, *, instructions: str, history: list[dict[str, Any]], index: int, said: str,
                notices: list[dict[str, Any]]) -> Turn:
    """One tutor reply with check_time available, answered from the simulated clock.

    Not streamed, because a tool call has to be read whole before it can be
    answered; this bench does not time the tutor, so nothing is lost. The call
    and its answer stay in ``history``, as they do in a LiveKit chat context.
    """
    input_tokens = cached_tokens = output_tokens = 0
    started = time.perf_counter()
    reply = ""
    for check in range(MAX_CLOCK_CHECKS + 1):
        kwargs: dict[str, Any] = {
            "model": TUTOR_MODEL, "messages": [{"role": "system", "content": instructions}, *history],
            "tools": [CHECK_TIME_TOOL], "tool_choice": "none" if check == MAX_CLOCK_CHECKS else "auto",
        }
        if TUTOR_MODEL.startswith(REASONING_MODEL_PREFIXES) and TUTOR_EFFORT.strip():
            kwargs["reasoning_effort"] = TUTOR_EFFORT.strip()
        response = client.chat.completions.create(**kwargs)
        usage = response.usage
        input_tokens += usage.prompt_tokens or 0
        output_tokens += usage.completion_tokens or 0
        cached_tokens += getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0
        message = response.choices[0].message
        if not message.tool_calls:
            reply = (message.content or "").strip()
            break
        status = clock_status(seconds_at(index))
        history.append({"role": "assistant", "content": message.content,
                        "tool_calls": [call.model_dump() for call in message.tool_calls]})
        for call in message.tool_calls:
            history.append({"role": "tool", "tool_call_id": call.id, "content": status})
        notices.append({"before": index, "kind": "check_time", "text": status})
    return Turn(index=index, ttft_s=None, latency_s=time.perf_counter() - started, output_tokens=output_tokens,
                input_tokens=input_tokens, cached_tokens=cached_tokens, bait=None, said=said, reply=reply)


# --- one debrief ------------------------------------------------------------

def scenario_prompt(scenario: dict[str, Any], variant: Variant) -> str:
    """The tutor's instructions for this case, with the variant's blocks swapped in."""
    return apply_variant(_debrief_prompt(scenario["context"]), variant.blocks)


def run_debrief(*, openai_client: Any, anthropic_client: Any, variant: Variant, scenario: dict[str, Any],
                persona_name: str, persona: dict[str, str], repeat: int) -> Debrief:
    """One debrief, the tutor and the simulated trainee taking turns, as a session would run it.

    The clock's marks go into the tutor's history as system lines as they pass,
    where ``apply_notice`` puts them in production, and stay there for the rest
    of the conversation; the tutor can call check_time. The trainee never hears
    any of it.
    """
    instructions = scenario_prompt(scenario, variant)
    greeting = variant.greeting or DEBRIEF_GREETING
    plan = scenario["context"]["station"]["management_plan"]
    debrief = Debrief(
        variant=variant.name, scenario=scenario["name"], persona=persona_name, repeat=repeat,
        greeting=greeting, never=never_list(instructions),
        plan_sections=ManagementPlanFormatter.section_titles(plan),
    )
    system = trainee_system(scenario, persona)
    tutor_history: list[dict[str, Any]] = [{"role": "assistant", "content": greeting}]
    trainee_history: list[dict[str, str]] = [{"role": "user", "content": greeting}]
    marks_sent = 0

    for index in range(TRAINEE_TURNS):
        said = trainee_line(anthropic_client, system, trainee_history, debrief.trainee_usage)
        # The trainee marks the end, sometimes after a last goodbye on the same line.
        finished = END_OF_DEBRIEF in said
        said = said.replace(END_OF_DEBRIEF, "").strip()
        if not said:
            debrief.ended_early_at = index
            break
        trainee_history.append({"role": "assistant", "content": said})
        pushed = marks_due(index, marks_sent)
        marks_sent += len(pushed)
        for note in pushed:
            tutor_history.append({"role": "system", "content": note})
            debrief.notices.append({"before": index, "kind": "mark", "text": note})
        tutor_history.append({"role": "user", "content": said})
        turn = timed_reply(openai_client, instructions=instructions, history=tutor_history, index=index,
                           said=said, notices=debrief.notices)
        debrief.turns.append(turn)
        tutor_history.append({"role": "assistant", "content": turn.reply})
        # An empty reply is the tutor going silent in the room; the trainee hears
        # nothing and reacts to that, and summarise counts it against the variant.
        trainee_history.append({"role": "user", "content": turn.reply or SILENCE})
        if finished:
            debrief.ended_early_at = index + 1
            break

    conversation = conversation_text(greeting, debrief.turns)
    debrief.questionnaire = ask_questionnaire(anthropic_client, system, conversation, debrief.trainee_usage)
    return debrief


# --- the judge --------------------------------------------------------------

def judge_tool(plan_sections: list[str]) -> dict[str, Any]:
    """The rubric, as a tool the judge is made to call."""
    scale = {"type": "integer", "minimum": 1, "maximum": 5}
    return {
        "name": "record_debrief_quality",
        "description": "Record how well the tutor ran this debrief.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "description": "Every management plan heading, each exactly once.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "enum": plan_sections},
                            "status": {"type": "string", "enum": ["built_together", "told", "missed"],
                                       "description": (
                                           "built_together: the trainee voiced their own reasoning or version "
                                           "of this part of the plan and the tutor built on it. told: the tutor "
                                           "explained it, without the trainee's thinking. missed: not discussed.")},
                        },
                        "required": ["title", "status"],
                    },
                },
                "plan_readout_turns": {"type": "integer", "minimum": 0, "description": (
                    "Tutor turns that recited three or more plan points in a row without asking for the "
                    "trainee's thinking.")},
                "interrogation": {**scale, "description": (
                    "1 = never felt like being questioned, 5 = a string of questions with little given back.")},
                "trainee_led": {**scale, "description": (
                    "1 = the tutor ran its own agenda regardless, 5 = the tutor followed the topics the trainee "
                    "chose and brought in the rest around them.")},
                "warmth": {**scale, "description": "1 = cold or judging, 5 = warm, encouraging and genuine."},
                "opened_with_structure": {"type": "boolean", "description": (
                    "In its first two turns, the tutor said briefly how the debrief would go.")},
                "roleplay_offered": {"type": "boolean"},
                "roleplay_happened": {"type": "boolean", "description": "The tutor spoke as the patient."},
                "roleplay_patient_turns": {"type": "integer", "minimum": 0,
                                           "description": "Tutor turns spoken as the patient."},
                "roleplay_exited_cleanly": {"type": ["boolean", "null"], "description": (
                    "If role-play happened: it said when it stepped in and out, stayed for the agreed moment "
                    "only, and went back to being the tutor. Null if it did not happen.")},
                "roleplay_faithful": {"type": ["boolean", "null"], "description": (
                    "If role-play happened: the patient said nothing the transcript and plan do not support. "
                    "Null if it did not happen.")},
                "clinical_teaching": {**scale, "description": (
                    "1 = generic communication advice that would fit any case, 5 = taught the specific medicine "
                    "of this case from the plan: the working diagnosis and why, the tests and what they are for, "
                    "drugs, doses and how to use them, follow-up, and exact safety-net thresholds, with the "
                    "reasoning behind them.")},
                "generic_turns": {"type": "integer", "minimum": 0, "description": (
                    "Tutor turns whose teaching would fit any consultation, tied to no line of the transcript "
                    "and no part of the plan. Greetings, acknowledgements and role-play lines do not count.")},
                "clinical_errors": {
                    "type": "array",
                    "description": "Medically wrong or unsafe things the tutor said, whatever their source.",
                    "items": {"type": "object", "properties": {
                        "turn": {"type": "integer"}, "quote": {"type": "string"}, "why": {"type": "string"},
                    }, "required": ["turn", "quote", "why"]},
                },
                "safety_gap_addressed": {"type": "boolean", "description": (
                    "The safety-critical gap below was named and put right in the debrief, whoever raised it.")},
                "trainee_named_takeaways": {"type": "boolean", "description": (
                    "Near the end, the trainee, not the tutor, said what they would take away.")},
                "invented_facts": {
                    "type": "array",
                    "description": "Things the tutor stated as fact about the case that the transcript, plan and marking do not support.",
                    "items": {"type": "object", "properties": {
                        "turn": {"type": "integer"}, "quote": {"type": "string"}, "why": {"type": "string"},
                    }, "required": ["turn", "quote", "why"]},
                },
                "breaches": {
                    "type": "array",
                    "description": "Breaches of the tutor's own never list, and only that list.",
                    "items": {"type": "object", "properties": {
                        "turn": {"type": "integer"}, "rule": {"type": "string"}, "quote": {"type": "string"},
                    }, "required": ["turn", "rule", "quote"]},
                },
                "summary": {"type": "string", "description": "Two sentences: what worked, what did not."},
            },
            "required": ["sections", "plan_readout_turns", "interrogation", "trainee_led", "warmth",
                         "clinical_teaching", "generic_turns", "clinical_errors",
                         "opened_with_structure", "roleplay_offered", "roleplay_happened", "roleplay_patient_turns",
                         "roleplay_exited_cleanly", "roleplay_faithful", "safety_gap_addressed",
                         "trainee_named_takeaways", "invented_facts", "breaches", "summary"],
        },
    }


def judge_debrief(client: Any, debrief: Debrief, scenario: dict[str, Any]) -> dict[str, Any]:
    """Score one debrief with Opus, against the case material and the variant's own never list.

    Each arm is held to the spec it was given: role-play breaks the baseline's
    rules and is allowed by the variants', and the judge is told which applies.
    """
    context = scenario["context"]
    never = "\n".join(f"- {rule}" for rule in debrief.never) or "- (none)"
    prompt = f"""Below is a simulated debrief after a GP trainee's practice SCA consultation. The tutor is a model under test; the trainee is simulated. Judge only the tutor.

The consultation it is debriefing:
<consultation>
{TranscriptFormatter.format(context["transcript"])}
</consultation>

The management plan the tutor was given:
<management_plan>
{ManagementPlanFormatter.format(context["station"]["management_plan"])}
</management_plan>

The marking the tutor was given:
<marking>
{marking_for(context.get("framework", "sca-rcgp-v1"), context["feedback"]).strip()}
</marking>

The safety-critical gap in this consultation: {scenario["trainee_brief"]["safety_critical_gap"]}

The tutor's own rules. It must never:
{never}
Count as a breach only something these rules forbid. A tutor explaining the plan, discussing the marking, or suggesting a better form of words is doing its job. If these rules allow a brief role-play as the patient, a bounded one is not a breach.

Classify each of these plan headings exactly once, returning each title exactly as written: {" | ".join(debrief.plan_sections)}
Judge the substance, not the label.

<debrief>
{conversation_text(debrief.greeting, debrief.turns, private_notices(debrief))}
</debrief>"""
    tool = judge_tool(debrief.plan_sections)
    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4096,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": prompt}],
    )
    _add_usage(debrief.judge_usage, message.usage)
    for block in message.content:
        if block.type == "tool_use":
            return dict(block.input)
    return {}


# --- summary ----------------------------------------------------------------

def section_shares(judged: dict[str, Any], plan_sections: list[str]) -> dict[str, float]:
    """The share of plan headings built together, told, and missed."""
    statuses = {entry.get("title"): entry.get("status") for entry in judged.get("sections", [])}
    count = len(plan_sections) or 1
    return {
        status: sum(1 for title in plan_sections if statuses.get(title, "missed") == status) / count
        for status in ("built_together", "told", "missed")
    }


def heading_misses(debriefs: list[Debrief]) -> dict[str, dict[str, tuple[int, int]]]:
    """Per variant, per plan heading: (debriefs that missed it, debriefs judged with it).

    The averaged `missed` share hides which heading goes: "the tutor missed the
    differential in 14 of 16 runs" (V-2) is this table, not that column.
    """
    counts: dict[str, dict[str, list[int]]] = {}
    for debrief in debriefs:
        if debrief.error is not None or not debrief.judge:
            continue
        statuses = {entry.get("title"): entry.get("status") for entry in debrief.judge.get("sections", [])}
        per_heading = counts.setdefault(debrief.variant, {})
        for title in debrief.plan_sections:
            missed_judged = per_heading.setdefault(title, [0, 0])
            missed_judged[1] += 1
            if statuses.get(title, "missed") == "missed":
                missed_judged[0] += 1
    return {
        variant: {title: (missed, judged) for title, (missed, judged) in headings.items()}
        for variant, headings in counts.items()
    }


def print_heading_misses(debriefs: list[Debrief]) -> None:
    """How often each plan heading was missed, by variant, as "missed/judged"."""
    table = heading_misses(debriefs)
    if not table:
        return
    variants = list(table)
    headings = list(dict.fromkeys(title for per_heading in table.values() for title in per_heading))
    print("\nplan headings missed (missed/judged)")
    print(f"{'heading':<38}" + "  ".join(f"{variant:>14}" for variant in variants))
    for title in headings:
        cells = []
        for variant in variants:
            missed, judged = table[variant].get(title, (0, 0))
            cells.append(f"{f'{missed}/{judged}' if judged else '-':>14}")
        print(f"{title:<38}" + "  ".join(cells))


def _mean(values: list[float]) -> float | None:
    """The mean, or None when there is nothing to average."""
    return statistics.mean(values) if values else None


def summarise(debriefs: list[Debrief]) -> list[dict[str, Any]]:
    """One row per variant, averaged over every scenario, persona and repeat."""
    rows = []
    for variant in dict.fromkeys(debrief.variant for debrief in debriefs):
        mine = [debrief for debrief in debriefs if debrief.variant == variant and debrief.error is None]
        judged = [debrief for debrief in mine if debrief.judge]
        talks = [talk_metrics(debrief.turns) for debrief in mine]
        shares = [section_shares(debrief.judge, debrief.plan_sections) for debrief in judged]
        played = [debrief for debrief in judged if debrief.judge.get("roleplay_happened")]
        answers = [debrief.questionnaire for debrief in mine if debrief.questionnaire]

        def judged_mean(key: str) -> float | None:
            """The judge's average for one numeric or boolean field."""
            return _mean([float(debrief.judge[key]) for debrief in judged if debrief.judge.get(key) is not None])

        def answered_mean(key: str) -> float | None:
            """The trainees' average for one questionnaire item."""
            return _mean([float(answer[key]) for answer in answers if answer.get(key) is not None])

        rows.append({
            "variant": variant,
            "debriefs": len(mine),
            "failed": sum(1 for debrief in debriefs if debrief.variant == variant and debrief.error),
            "built_together": _mean([share["built_together"] for share in shares]),
            "told": _mean([share["told"] for share in shares]),
            "missed": _mean([share["missed"] for share in shares]),
            "clinical_teaching": judged_mean("clinical_teaching"),
            "generic_turns": judged_mean("generic_turns"),
            "clinical_errors": _mean([float(len(debrief.judge.get("clinical_errors", []))) for debrief in judged]),
            "exchanges": _mean([float(len(debrief.turns)) for debrief in mine]),
            "silent_replies": _mean([float(sum(1 for turn in debrief.turns if not turn.reply)) for debrief in mine]),
            "clock_checks": _mean([float(sum(1 for notice in debrief.notices if notice["kind"] == "check_time"))
                                   for debrief in mine]),
            "clock_talk": _mean([float(sum(1 for turn in debrief.turns if CLOCK_TALK.search(turn.reply)))
                                 for debrief in mine]),
            "readout_turns": judged_mean("plan_readout_turns"),
            "interrogation": judged_mean("interrogation"),
            "trainee_led": judged_mean("trainee_led"),
            "warmth": judged_mean("warmth"),
            "opened_with_structure": judged_mean("opened_with_structure"),
            "safety_gap_addressed": judged_mean("safety_gap_addressed"),
            "trainee_named_takeaways": judged_mean("trainee_named_takeaways"),
            "roleplay_happened": len(played) / len(judged) if judged else None,
            "roleplay_unclean": sum(1 for debrief in played if debrief.judge.get("roleplay_exited_cleanly") is False),
            "roleplay_unfaithful": sum(1 for debrief in played if debrief.judge.get("roleplay_faithful") is False),
            "invented_facts": _mean([float(len(debrief.judge.get("invented_facts", []))) for debrief in judged]),
            "breaches": _mean([float(len(debrief.judge.get("breaches", []))) for debrief in judged]),
            "felt_safe": answered_mean("felt_safe"),
            "felt_interrogated": answered_mean("felt_interrogated"),
            "understands_plan": answered_mean("understands_plan_better"),
            "practised": answered_mean("practised_hard_moment"),
            "would_use_again": answered_mean("would_use_again"),
            "tutor_share": _mean([talk["tutor_share"] for talk in talks]),
            "mean_tutor_words": _mean([talk["mean_tutor_words"] for talk in talks]),
            "longest_tutor_words": _mean([talk["longest_tutor_words"] for talk in talks]),
            "questions_per_turn": _mean([talk["questions_per_turn"] for talk in talks]),
            "stacked_questions": _mean([talk["stacked_question_turns"] for talk in talks]),
            "cost_per_debrief": _mean([debrief.cost_usd() for debrief in mine]),
        })
    return rows


def composite(row: dict[str, Any]) -> float | None:
    """One number to rank on, each part scaled to 0..1 with higher better.

    Plan sections built together, how specifically the medicine was taught, the
    trainee's sense of safety, understanding
    and not being quizzed, and the judge's interrogation and trainee-led scores,
    weighted equally. Gates come first; this only orders what passes them.
    """
    parts = [
        row["built_together"],
        None if row.get("clinical_teaching") is None else (row["clinical_teaching"] - 1) / 4,
        None if row["felt_safe"] is None else (row["felt_safe"] - 1) / 4,
        None if row["understands_plan"] is None else (row["understands_plan"] - 1) / 4,
        None if row["felt_interrogated"] is None else (5 - row["felt_interrogated"]) / 4,
        None if row["interrogation"] is None else (5 - row["interrogation"]) / 4,
        None if row["trainee_led"] is None else (row["trainee_led"] - 1) / 4,
    ]
    present = [part for part in parts if part is not None]
    return statistics.mean(present) if present else None


def gate_failures(row: dict[str, Any], baseline: dict[str, Any] | None) -> list[str]:
    """Why a variant cannot ship whatever its score: invention, breaches, or a role-play left running."""
    reasons = []
    if baseline is not None and row["variant"] != baseline["variant"]:
        if (row["invented_facts"] or 0) > (baseline["invented_facts"] or 0):
            reasons.append("invents more than baseline")
        if (row["breaches"] or 0) > (baseline["breaches"] or 0):
            reasons.append("breaches more than baseline")
        if (row.get("clinical_errors") or 0) > (baseline.get("clinical_errors") or 0):
            reasons.append("more clinical errors than baseline")
    if row["roleplay_unclean"]:
        reasons.append(f"{row['roleplay_unclean']} role-play(s) not exited cleanly")
    if row["roleplay_unfaithful"]:
        reasons.append(f"{row['roleplay_unfaithful']} role-play(s) invented as the patient")
    return reasons


def _cell(value: Any, digits: int = 2) -> str:
    """A table cell: numbers rounded, missing values as a dash."""
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def print_report(rows: list[dict[str, Any]]) -> None:
    """The comparison table, ranked, with gates, and the questionnaire beside the judge."""
    baseline = next((row for row in rows if row["variant"] == BASELINE), None)
    ranked = sorted(rows, key=lambda row: composite(row) or 0.0, reverse=True)
    columns = [
        ("variant", "variant"), ("n", "debriefs"), ("exch", "exchanges"), ("medicine", "clinical_teaching"),
        ("generic", "generic_turns"), ("clin_err", "clinical_errors"), ("built", "built_together"), ("told", "told"),
        ("missed", "missed"), ("readout", "readout_turns"), ("interrog", "interrogation"),
        ("led", "trainee_led"), ("warm", "warmth"), ("struct", "opened_with_structure"),
        ("safety", "safety_gap_addressed"), ("takeaway", "trainee_named_takeaways"),
        ("rp", "roleplay_happened"), ("invent", "invented_facts"), ("breach", "breaches"),
    ]
    trainee_columns = [
        ("variant", "variant"), ("safe", "felt_safe"), ("quizzed", "felt_interrogated"),
        ("clearer", "understands_plan"), ("practised", "practised"), ("again", "would_use_again"),
        ("tutor%", "tutor_share"), ("words", "mean_tutor_words"), ("longest", "longest_tutor_words"),
        ("q/turn", "questions_per_turn"), ("stacked", "stacked_questions"), ("silent", "silent_replies"), ("checks", "clock_checks"),
        ("clocktalk", "clock_talk"), ("$", "cost_per_debrief"),
    ]
    for title, table in (("judge", columns), ("trainee and talk", trainee_columns)):
        print(f"\n{title}")
        print("  ".join(f"{label:>10}" for label, _key in table))
        for row in ranked:
            print("  ".join(f"{_cell(row.get(key)):>10}" for _label, key in table))
    print("\nranking (gates first, then composite)")
    for row in ranked:
        failures = gate_failures(row, baseline)
        status = "BLOCKED: " + "; ".join(failures) if failures else "passes gates"
        print(f"  {row['variant']:<28} composite {_cell(composite(row))}  {status}")


# --- commands ---------------------------------------------------------------

def load_scenarios(names: list[str]) -> dict[str, dict[str, Any]]:
    """The named debrief scenarios from bench/debrief."""
    return {name: json.loads((DEBRIEF_BENCH / f"{name}.json").read_text()) for name in names}


def estimate_usd(scenarios: dict[str, dict[str, Any]], variants: list[Variant], personas: int, repeats: int) -> float:
    """A deliberately pessimistic cost before anything is spent, from prompt sizes at four characters a token."""
    total = 0.0
    tutor_in, tutor_cached, tutor_out = PRICES[TUTOR_MODEL]
    trainee_in, trainee_read, trainee_write, trainee_out = CLAUDE_PRICES[TRAINEE_MODEL]
    judge_in, _judge_read, _judge_write, judge_out = CLAUDE_PRICES[JUDGE_MODEL]
    history_tokens = TRAINEE_TURNS * 150
    for scenario in scenarios.values():
        for variant in variants:
            prompt_tokens = len(scenario_prompt(scenario, variant)) / 4
            trainee_tokens = len(trainee_system(scenario, {"personality": "", "on_rehearsal": ""})) / 4 + 150
            per_turn_tutor = prompt_tokens + history_tokens / 2
            tutor = TRAINEE_TURNS * (per_turn_tutor * (0.3 * tutor_in + 0.7 * tutor_cached) + 120 * tutor_out)
            trainee = TRAINEE_TURNS * (trainee_tokens * trainee_read + history_tokens / 2 * trainee_in
                                       + 60 * trainee_out) + trainee_tokens * trainee_write
            questionnaire = (trainee_tokens + history_tokens * 1.5) * trainee_in + 300 * trainee_out
            judge = (prompt_tokens + history_tokens * 1.5) * judge_in + 1500 * judge_out
            total += (tutor + trainee + questionnaire + judge) / 1_000_000 * personas * repeats
    return total


def _write(out: Path, meta: dict[str, Any], debriefs: list[Debrief]) -> None:
    """Save everything so far; called after each debrief, so a crash loses one, not all."""
    out.parent.mkdir(parents=True, exist_ok=True)
    finished = sorted(debriefs, key=lambda debrief: (debrief.variant, debrief.scenario, debrief.persona, debrief.repeat))
    out.write_text(json.dumps({**meta, "summary": summarise(finished),
                               "debriefs": [asdict(debrief) for debrief in finished]}, indent=2))


def _debrief_from(raw: dict[str, Any]) -> Debrief:
    """A saved debrief, back as a Debrief."""
    turns = [Turn(**turn) for turn in raw.pop("turns")]
    return Debrief(**raw, turns=turns)


def cmd_run(args: argparse.Namespace) -> int:
    """Run every variant on every scenario and persona, judge it, and save it."""
    import anthropic
    from openai import OpenAI

    variants = [load_variant(name.strip()) for name in args.variants.split(",") if name.strip()]
    scenarios = load_scenarios([name.strip() for name in args.scenarios.split(",") if name.strip()])
    all_personas = json.loads((DEBRIEF_BENCH / "personas.json").read_text())
    persona_names = [name.strip() for name in args.personas.split(",") if name.strip()] or list(all_personas)
    for scenario in scenarios.values():
        for variant in variants:
            scenario_prompt(scenario, variant)  # fail on a bad variant before spending anything

    jobs = [(variant, scenario, persona, repeat) for variant in variants for scenario in scenarios.values()
            for persona in persona_names for repeat in range(args.repeats)]
    estimate = estimate_usd(scenarios, variants, len(persona_names), args.repeats)
    print(f"{len(jobs)} debriefs, estimated ${estimate:.2f} (cap ${args.max_usd:.2f})", file=sys.stderr)
    if estimate > args.max_usd:
        print("over the cap; raise --max-usd once the spend is approved", file=sys.stderr)
        return 2

    openai_client, anthropic_client = OpenAI(), anthropic.Anthropic(max_retries=6)
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(), "tutor_model": TUTOR_MODEL,
            "trainee_model": TRAINEE_MODEL, "judge_model": JUDGE_MODEL, "estimate_usd": estimate}
    out = Path(args.out)
    done: list[Debrief] = []
    lock = threading.Lock()

    def one(job: tuple[Variant, dict[str, Any], str, int]) -> Debrief:
        """Run and judge one debrief; a failure is recorded, not raised, so the batch goes on."""
        variant, scenario, persona_name, repeat = job
        try:
            debrief = run_debrief(
                openai_client=openai_client, anthropic_client=anthropic_client, variant=variant,
                scenario=scenario, persona_name=persona_name, persona=all_personas[persona_name], repeat=repeat,
            )
            if not args.no_judge:
                debrief.judge = judge_debrief(anthropic_client, debrief, scenario)
        except Exception as exc:  # noqa: BLE001 — one failed debrief must not lose the other seventy nine
            debrief = Debrief(variant=variant.name, scenario=scenario["name"], persona=persona_name, repeat=repeat,
                              greeting="", never=[], plan_sections=[], error=f"{type(exc).__name__}: {exc}")
        return debrief

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(one, job) for job in jobs]):
            debrief = future.result()
            with lock:
                done.append(debrief)
                _write(out, meta, done)
            state = f"FAILED {debrief.error}" if debrief.error else f"${debrief.cost_usd():.3f}"
            print(f"  [{len(done)}/{len(jobs)}] {debrief.variant} {debrief.scenario} {debrief.persona} "
                  f"#{debrief.repeat + 1} {state}", file=sys.stderr, flush=True)

    spent = sum(debrief.cost_usd() for debrief in done)
    print_report(summarise(done))
    print_heading_misses(done)
    print(f"\nspent ${spent:.2f}; full debriefs: {out}")
    return 0


def cmd_rejudge(args: argparse.Namespace) -> int:
    """Re-score saved debriefs and show how far each summary number moved: the judge's noise floor."""
    import anthropic

    data = json.loads(Path(args.results).read_text())
    debriefs = [_debrief_from(raw) for raw in data["debriefs"]]
    before = {row["variant"]: row for row in data["summary"]}
    scenarios = load_scenarios(sorted({debrief.scenario for debrief in debriefs}))
    client = anthropic.Anthropic(max_retries=6)

    def rejudge(debrief: Debrief) -> None:
        """Keep the old verdict and add a fresh one."""
        if debrief.error:
            return
        debrief.earlier_judges.append(debrief.judge)
        debrief.judge = judge_debrief(client, debrief, scenarios[debrief.scenario])

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(rejudge, debriefs))
    data["summary"] = summarise(debriefs)
    data["debriefs"] = [asdict(debrief) for debrief in debriefs]
    data["rejudged_at"] = datetime.now(timezone.utc).isoformat()
    Path(args.results).write_text(json.dumps(data, indent=2))
    print_report(data["summary"])
    print_heading_misses(debriefs)
    print("\njudge drift (this pass minus the last), per variant")
    keys = ("built_together", "clinical_teaching", "interrogation", "trainee_led", "warmth", "invented_facts",
            "breaches")
    for row in data["summary"]:
        old = before.get(row["variant"], {})
        drift = "  ".join(
            f"{key} {row[key] - old[key]:+.2f}" for key in keys
            if row.get(key) is not None and old.get(key) is not None
        )
        print(f"  {row['variant']:<28} {drift}")
    return 0


PAIRWISE_TOOL: dict[str, Any] = {
    "name": "record_preference",
    "description": "Which debrief was better for this trainee.",
    "input_schema": {
        "type": "object",
        "properties": {
            "better": {"type": "string", "enum": ["1", "2", "tie"]},
            "reason": {"type": "string", "description": "One sentence."},
        },
        "required": ["better", "reason"],
    },
}


def cmd_pairwise(args: argparse.Namespace) -> int:
    """A blinded tie-break: the same case and trainee under two variants, in random order."""
    import anthropic

    data = json.loads(Path(args.results).read_text())
    debriefs = [_debrief_from(raw) for raw in data["debriefs"] if not raw.get("error")]
    by_case = {(debrief.variant, debrief.scenario, debrief.persona, debrief.repeat): debrief for debrief in debriefs}
    pairs = [(debrief, by_case[(args.second, debrief.scenario, debrief.persona, debrief.repeat)])
             for debrief in debriefs if debrief.variant == args.first
             and (args.second, debrief.scenario, debrief.persona, debrief.repeat) in by_case]
    client = anthropic.Anthropic(max_retries=6)
    # Order each pair up front: the judge must not learn that the first is always one variant.
    shuffler = random.Random(args.seed)
    orderings = [shuffler.sample(pair, k=2) for pair in pairs]

    def prefer(ordered: list[Debrief]) -> str:
        """Which variant won this pair, or tie."""
        prompt = (
            "Two tutors debriefed the same GP trainee on the same practice consultation. Which debrief would "
            "leave this trainee knowing the medicine of this case better, with the management plan understood "
            "rather than recited, having done more of the thinking themselves, without feeling quizzed or "
            "judged?\n\n"
            + "\n\n".join(f"<debrief_{number}>\n{conversation_text(item.greeting, item.turns)}\n</debrief_{number}>"
                          for number, item in enumerate(ordered, start=1))
        )
        message = client.messages.create(
            model=JUDGE_MODEL, max_tokens=500, tools=[PAIRWISE_TOOL],
            tool_choice={"type": "tool", "name": PAIRWISE_TOOL["name"]},
            messages=[{"role": "user", "content": prompt}],
        )
        choice = next((dict(block.input) for block in message.content if block.type == "tool_use"), {})
        if choice.get("better") in ("1", "2"):
            return ordered[int(choice["better"]) - 1].variant
        return "tie"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outcomes = list(pool.map(prefer, orderings))
    print(f"{len(pairs)} matched pairs: {args.first} {outcomes.count(args.first)}, "
          f"{args.second} {outcomes.count(args.second)}, tie {outcomes.count('tie')}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Re-print the table from a saved run."""
    data = json.loads(Path(args.results).read_text())
    print_report(data["summary"])
    print_heading_misses([_debrief_from(raw) for raw in data.get("debriefs", [])])
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    default_variants = ",".join([BASELINE, *sorted(path.stem for path in VARIANTS.glob("*.txt"))])
    default_scenarios = ",".join(sorted(path.stem for path in DEBRIEF_BENCH.glob("*.json") if path.stem != "personas"))

    run = sub.add_parser("run", help="debrief each persona under each variant, and score it")
    run.add_argument("--variants", default=default_variants, help=f"comma-separated; '{BASELINE}' is the shipped prompt")
    run.add_argument("--scenarios", default=default_scenarios)
    run.add_argument("--personas", default="", help="comma-separated; defaults to all")
    run.add_argument("--repeats", type=int, default=2)
    run.add_argument("--workers", type=int, default=6)
    run.add_argument("--max-usd", type=float, default=50.0, help="refuse to start if the estimate is higher")
    run.add_argument("--no-judge", action="store_true")
    run.add_argument("--out", default="runs/debrief.json")

    rejudge = sub.add_parser("rejudge", help="re-score saved debriefs and show the judge's drift")
    rejudge.add_argument("results")
    rejudge.add_argument("--workers", type=int, default=4)

    pairwise = sub.add_parser("pairwise", help="blinded head-to-head of two variants on matched debriefs")
    pairwise.add_argument("results")
    pairwise.add_argument("--first", required=True)
    pairwise.add_argument("--second", default=BASELINE)
    pairwise.add_argument("--seed", type=int, default=7)
    pairwise.add_argument("--workers", type=int, default=4)

    report = sub.add_parser("report", help="re-print the table from a saved run")
    report.add_argument("results")

    args = parser.parse_args(argv)
    commands = {"run": cmd_run, "rejudge": cmd_rejudge, "pairwise": cmd_pairwise, "report": cmd_report}
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
