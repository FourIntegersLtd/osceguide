#!/usr/bin/env python3
"""Compare voice models on the thing that actually breaks: staying in role.

    run      replay a scripted consultation against each model and score it
    rejudge  re-score saved transcripts against the current breach spec
    report   re-print the table from a saved run

The cheapest model that holds the persona wins. Newer and larger are not
arguments; the numbers this produces are. So every arm runs the same prompt,
the same per-turn reminder and the same doctor script, and the only thing that
varies is the model under test.

What it measures, per arm: role breaches over a full consultation, time to
first token, whole-response latency, output tokens, and cost per consultation
computed from the usage the API actually reported rather than from an estimate.

What it cannot measure: barge-in and recovery, which need real audio and a
real session. Shortlist here, then confirm those live with `make dev-assessment`
and read the `[LATENCY:...]` lines the worker already logs.

Examples:
    poetry run python scripts/model_bench.py run --arms gpt-4o-mini,gpt-5.4-nano --repeats 3
    poetry run python scripts/model_bench.py run --role tutor --arms gpt-4o,gpt-5.4-mini --repeats 2
    poetry run python scripts/model_bench.py report runs/bench-patient.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))

from osce_assessment.prompts._blocks import DOCTOR_NEVER, EXAMINER_NEVER, PATIENT_NEVER  # noqa: E402
from osce_assessment.prompts.debrief_prompt import TUTOR_NEVER  # noqa: E402
from osce_assessment.prompts import (  # noqa: E402
    AthenaDoctorFormatter,
    ConversationPromptFormatter,
    DebriefPromptFormatter,
    ManagementPlanFormatter,
    OrthoFeedbackFormatter,
    OrthoPromptFormatter,
    PlabFeedbackFormatter,
    ScaFeedbackFormatter,
    TranscriptFormatter,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPT = ROOT / "scripts" / "bench" / "doctor_sca_chest_pain.json"
STATIONS = ROOT / "tests" / "fixtures" / "stations"
FEEDBACK = ROOT / "tests" / "fixtures" / "feedback"

# Published list prices, dollars per million tokens: (input, cached input, output).
# Cached input dominates a voice consultation, because the system prompt is
# resent on every turn and is the same bytes every time. Refresh from
# https://developers.openai.com/api/docs/pricing when a model is added.
PRICES: dict[str, tuple[float, float, float]] = {
    "gpt-4o-mini": (0.15, 0.075, 0.60),
    "gpt-4o": (2.50, 1.25, 10.00),
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4": (2.50, 0.25, 15.00),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-5.6-terra": (2.00, 0.20, 12.00),
}

# Mirrors voice_infra.speech._openai_llm. Kept as a local rule rather than an
# import because importing the worker's speech module pulls in all of LiveKit,
# and a benchmark that needs a media stack to run is a benchmark nobody runs.
REASONING_MODEL_PREFIX = "gpt-5"

JUDGE_MODEL = "claude-opus-5"

# Re-scoring identical transcripts gave 0.0 breaches on one pass and 0.7 on
# another, so anything under about one breach per consultation is the judge
# moving, not the model. A candidate has to beat that to be worth paying for.
MEANINGFUL_BREACH_DELTA = 1.0

# Re-sending a one-line role reminder on every turn was tried in production and
# measured away: it bought nothing on the patient and made the consulting doctor
# worse. The text lives here rather than in the engine so the experiment stays
# repeatable without the engine carrying something nothing ships.
REMINDERS = {
    "patient": (
        "You are the patient and the person speaking is the doctor. "
        "Answer only as the patient: never ask the doctor clinical questions, and never diagnose, "
        "examine, advise, safety-net or summarise the consultation."
    ),
    "tutor": (
        "You are the tutor debriefing the doctor about a consultation that has already finished. "
        "You were not in that consultation: never re-enact it and never invent anything that is not "
        "in the transcript."
    ),
    "doctor": (
        "You are the doctor and the person speaking is the patient. "
        "Work through the management plan heading by heading in the order you were given, and do not "
        "move on from a heading until you have said its content aloud."
    ),
    "examiner": (
        "You are the examiner and the person speaking is the candidate being examined. "
        "Ask and probe only: never answer your own question, never teach or hint, and never tell the "
        "candidate how they are doing."
    ),
}

# The breach lists are the prompt's own, not a second list written here. A judge
# scoring against a stricter spec than the model was given invents breaches: the
# first run of this harness marked a tutor down for disclosing the marking and
# for suggesting better phrasing, both of which the debrief prompt asks for.
ROLES = {
    "patient": {
        "persona": "the simulated patient",
        "counterpart": "the doctor",
        "reminder": REMINDERS["patient"],
        "breaches": PATIENT_NEVER,
    },
    # The tutor model serves the debrief. An examiner station is dispatched in
    # patient mode and so runs on the patient model, which is why it is not an
    # arm here: benchmarking it would be benchmarking the patient model twice.
    "tutor": {
        "persona": "the debrief tutor",
        "counterpart": "the doctor being debriefed",
        "reminder": REMINDERS["tutor"],
        "breaches": TUTOR_NEVER,
    },
    # The consulting doctor is the inverted persona: the model is the clinician
    # and the learner is the patient. What fails here is not who it is but how
    # much of the management plan it gets through, so this arm is also scored on
    # coverage.
    "doctor": {
        "persona": "the doctor",
        "counterpart": "the patient",
        "reminder": REMINDERS["doctor"],
        "breaches": DOCTOR_NEVER,
    },
    # Orthopaedics inverts the consultation entirely: the model examines and the
    # human is under examination. It is dispatched in patient mode, so in
    # production it runs on the patient model, not the tutor one.
    "examiner": {
        "persona": "the examiner",
        "counterpart": "the candidate",
        "reminder": REMINDERS["examiner"],
        "breaches": EXAMINER_NEVER,
    },
}

# A first pass that needs no model. These catch the unambiguous breaches cheaply
# and give the judge's findings something independent to agree with. This is
# measurement only; the worker has no such filter.
#
# Teach-back is the one place a patient legitimately says a doctor's words back:
# asked "tell me what you'd do if it got worse", answering is correct, and a
# patient who refuses is the one behaving oddly. Without this the filter fired
# on every consultation for doing the right thing.
INVITED_TEACH_BACK = re.compile(r"summaris|summariz|say (that )?back|tell me back|what (would )?you.?d do", re.I)
PATIENT_BREACH_PATTERNS = (
    (re.compile(r"\b(I'd|I would|we should|let's) (recommend|arrange|prescribe|refer|start you)\b", re.I), "gives management"),
    (re.compile(r"\b(differential|working diagnosis|rule out|red flags?)\b", re.I), "clinical reasoning aloud"),
    (re.compile(r"\b(on examination|I'll examine|let me examine|palpat)\w*\b", re.I), "examines"),
    (re.compile(r"\b(if it gets worse|call 999|safety.?net|come back if)\b", re.I), "safety-nets"),
    (re.compile(r"\b(as your doctor|I'm an AI|language model|as an AI)\b", re.I), "breaks character"),
    (re.compile(r"\b(what brings you in|how can I help you today|any other symptoms\?)", re.I), "takes the history"),
)


@dataclass
class Turn:
    index: int
    ttft_s: float | None
    latency_s: float
    output_tokens: int
    input_tokens: int
    cached_tokens: int
    bait: str | None
    said: str
    reply: str


@dataclass
class Run:
    arm: str
    role: str
    repeat: int
    turns: list[Turn] = field(default_factory=list)
    flagged: list[dict[str, Any]] = field(default_factory=list)
    judge: dict[str, Any] = field(default_factory=dict)
    # The management-plan headings this consultation was supposed to get through.
    # Empty for personas that have no plan to work through.
    plan_sections: list[str] = field(default_factory=list)
    # The subset a patient must not leave without. Tracked apart from the rest
    # because the two can move in opposite directions: a consultation that drops
    # health education to explain the diagnosis properly has got better, and a
    # single coverage number would call that a regression.
    core_sections: list[str] = field(default_factory=list)

    def _covered(self, against: list[str]) -> float | None:
        if not against:
            return None
        covered = {str(t) for t in self.judge.get("plan_sections_covered", [])}
        return len(covered & set(against)) / len(against)

    def coverage(self) -> float | None:
        """The share of deliverable plan headings the doctor actually said aloud."""
        return self._covered(self.plan_sections)

    def core_coverage(self) -> float | None:
        """The share of the headings a patient must not leave without."""
        return self._covered(self.core_sections)

    def cost_usd(self) -> float:
        rate_in, rate_cached, rate_out = PRICES.get(self.arm, (0.0, 0.0, 0.0))
        fresh = sum(t.input_tokens - t.cached_tokens for t in self.turns)
        cached = sum(t.cached_tokens for t in self.turns)
        out = sum(t.output_tokens for t in self.turns)
        return (fresh * rate_in + cached * rate_cached + out * rate_out) / 1_000_000


def render_prompt(role: str, script: dict) -> tuple[str, str]:
    """The instructions and the per-turn reminder a real session would be given.

    Rendered through the same formatters the backends call, so an arm is scored
    on the prompt production actually ships rather than on a copy of it.
    """
    reminder = ROLES[role]["reminder"]
    if role == "tutor":
        return _debrief_prompt(script["context"]), reminder
    if role == "examiner":
        station = json.loads((STATIONS / f"{script['station']}.json").read_text())
        return OrthoPromptFormatter.create_ortho_prompt(station), reminder
    if role == "doctor":
        context = script["context"]
        return AthenaDoctorFormatter.create_prompt(
            context["station_name"], context["doctor_information"], context["management_plan"]
        ), reminder
    station = json.loads((STATIONS / f"{script['station']}.json").read_text())
    return ConversationPromptFormatter.create_prompt(station), reminder


def _debrief_prompt(context: dict) -> str:
    """The tutor prompt, assembled the way the dispatching backend assembles it.

    An orthopaedic debrief is a different document from a consultation debrief:
    the plan slot holds the station's interview questions rather than a
    management plan, and the marking is the orthopaedic competency set. Both
    backends pass every framework's feedback formatter regardless, so this does
    too, or the prompt would not be the one production renders.
    """
    framework = context.get("framework", "sca-rcgp-v1")
    is_ortho = framework == "ortho-frcs-v1"
    feedback = json.loads((FEEDBACK / f"{context.get('feedback_fixture', 'sca_feedback')}.json").read_text())
    station = context.get("station") or {}
    transcript = TranscriptFormatter.format(context["transcript"])
    station_type = station.get("station_type") or feedback.get("station_type", "") or ""
    return DebriefPromptFormatter.create_prompt(
        transcript=transcript,
        management_plan=ManagementPlanFormatter.format(
            station.get("management_plan"), interview_questions=is_ortho, station_obj=station
        ),
        sca_feedback=ScaFeedbackFormatter.format(feedback),
        plab_feedback=PlabFeedbackFormatter.format(feedback),
        ortho_feedback=OrthoFeedbackFormatter.format(feedback, station_type=station_type) if is_ortho else "",
        station_type=station_type,
    )


def replay(*, arm: str, role: str, repeat: int, script: dict, effort: str,
           instructions: str | None = None, use_reminder: bool = False) -> Run:
    """One consultation, turn by turn, exactly as the worker would drive it.

    ``instructions`` and ``use_reminder`` exist for the ablation that has to run
    before any model is credited with fixing role drift: the same model, on the
    prompt it used to have, with and without the per-turn reminder.
    """
    from openai import OpenAI

    client = OpenAI()
    rendered, reminder = render_prompt(role, script)
    instructions = instructions if instructions is not None else rendered
    if not use_reminder:
        reminder = ""
    run = Run(arm=arm, role=role, repeat=repeat)
    history: list[dict[str, str]] = []

    for index, turn in enumerate(script["turns"]):
        # The worker appends the reminder to a throwaway copy of the context, so
        # it reaches every generation and accumulates in none. Same here.
        messages = [{"role": "system", "content": instructions}, *history]
        if reminder:
            messages.append({"role": "system", "content": reminder})
        messages.append({"role": "user", "content": turn["say"]})
        kwargs: dict[str, Any] = {
            "model": arm, "messages": messages, "stream": True,
            "stream_options": {"include_usage": True},
        }
        if arm.startswith(REASONING_MODEL_PREFIX) and effort.strip():
            kwargs["reasoning_effort"] = effort.strip()

        started = time.perf_counter()
        first: float | None = None
        chunks: list[str] = []
        usage: Any = None
        for event in client.chat.completions.create(**kwargs):
            if event.usage is not None:
                usage = event.usage
            if not event.choices:
                continue
            piece = event.choices[0].delta.content
            if piece:
                if first is None:
                    first = time.perf_counter() - started
                chunks.append(piece)
        reply = "".join(chunks).strip()
        cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0

        run.turns.append(Turn(
            index=index,
            ttft_s=first,
            latency_s=time.perf_counter() - started,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            cached_tokens=cached,
            bait=turn.get("bait"),
            said=turn["say"],
            reply=reply,
        ))
        history += [{"role": "user", "content": turn["say"]}, {"role": "assistant", "content": reply}]

    run.flagged = prefilter(run, role)
    if role == "doctor":
        # Only the patient-facing headings: a plan also holds notes to the
        # clinician, and scoring "check mood" as unsaid measures nothing.
        plan = script["context"]["management_plan"]
        run.plan_sections = ManagementPlanFormatter.section_titles(plan, audience="patient")
        run.core_sections = ManagementPlanFormatter.section_titles(plan, audience="patient", priority="core")
    return run


def prefilter(run: Run, role: str) -> list[dict[str, Any]]:
    """Unambiguous breaches, found without a model."""
    if role != "patient":
        return []
    hits = []
    for turn in run.turns:
        invited = bool(INVITED_TEACH_BACK.search(turn.said))
        for pattern, label in PATIENT_BREACH_PATTERNS:
            if invited and label == "safety-nets":
                continue
            found = pattern.search(turn.reply)
            if found:
                hits.append({"turn": turn.index, "kind": label, "quote": found.group(0), "bait": turn.bait})
    return hits


def judge_tool(*, plan_sections: list[str], exam_structure: bool = False) -> dict[str, Any]:
    """The judge's reply shape.

    Coverage is only asked for when there is a plan, and the exam structure only
    for the persona that has one to follow. A consultation station is marked on
    sequence as well as content: red flags and the medication list belong in the
    history, before any management is discussed.
    """
    properties: dict[str, Any] = {
        "breaches": {
            "type": "array",
            "description": "One entry per turn where the role was broken. Empty if none.",
            "items": {
                "type": "object",
                "properties": {
                    "turn": {"type": "integer", "description": "Index of the offending reply."},
                    "kind": {"type": "string", "description": "Which listed breach it is."},
                    "quote": {"type": "string", "description": "The words that broke the role."},
                },
                "required": ["turn", "kind", "quote"],
            },
        },
        "persona_consistency": {
            "type": "integer",
            "description": "1 to 5. Does this read as one consistent person throughout, with facts that do not contradict each other?",
        },
        "conversational_quality": {
            "type": "integer",
            "description": "1 to 5. Does it sound like real speech, answering what was asked, neither robotic nor over-talking?",
        },
        "summary": {"type": "string", "description": "Two sentences on how this transcript held up."},
    }
    required = ["breaches", "persona_consistency", "conversational_quality", "summary"]

    if plan_sections:
        headings = " | ".join(f"\"{title}\"" for title in plan_sections)
        properties["plan_sections_covered"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                f"Which of these headings had their content actually said aloud to the patient: {headings}. "
                "A heading counts only if its substance was spoken, not merely alluded to."
            ),
        }
        properties["plan_sections_missed"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "The headings from that same list whose content was never said aloud.",
        }
        required += ["plan_sections_covered", "plan_sections_missed"]

    if exam_structure:
        properties["exam_structure"] = {
            "type": "object",
            "description": "Whether the consultation followed the structure a station is marked on.",
            "properties": {
                "history_before_management": {
                    "type": "boolean",
                    "description": "Was the history taken before any management, treatment or follow-up was discussed?",
                },
                "red_flags_checked": {
                    "type": "boolean",
                    "description": "Did the doctor screen for red flags relevant to this presentation during the history?",
                },
                "medications_reviewed": {
                    "type": "boolean",
                    "description": "Did the doctor go through the patient's current medication during the history?",
                },
                "ice_explored": {
                    "type": "boolean",
                    "description": "Did the doctor explore the patient's ideas, concerns and expectations?",
                },
                "management_started_at_turn": {
                    "type": "integer",
                    "description": "Index of the first turn that discussed management, treatment or follow-up.",
                },
            },
            "required": ["history_before_management", "red_flags_checked", "medications_reviewed",
                         "ice_explored", "management_started_at_turn"],
        }
        required.append("exam_structure")

    return {
        "name": "record_role_adherence",
        "description": "Record where the simulated participant left its role, and what it covered.",
        "input_schema": {"type": "object", "properties": properties, "required": required},
    }


def judge(run: Run, role: str) -> dict[str, Any]:
    """Score one transcript with a model from a different family than the arms.

    A different family on purpose: an OpenAI model grading OpenAI transcripts
    has a thumb on the scale.
    """
    import anthropic

    spec = ROLES[role]
    breaches = "\n".join(f"- {b}" for b in spec["breaches"])
    transcript = "\n\n".join(
        f"[turn {t.index}] {spec['counterpart'].upper()}: {t.said}\n[turn {t.index}] THEM: {t.reply}"
        for t in run.turns
    )
    plan_note = ""
    if run.plan_sections:
        plan_note = (
            "\n\nThis is a consultation station, marked on sequence as well as content: the history, "
            "including red flags and a review of the current medication, belongs before any management "
            "is discussed. Report whether that held.\n"
            "\n\nThis persona was given a management plan to work through, under these headings, in this "
            f"order: {' | '.join(chr(34) + t + chr(34) for t in run.plan_sections)}.\n"
            "Those are pipe-separated because one of them contains commas; return each one exactly as "
            "written.\nSay which of them it actually conveyed to the patient. "
            "Judge the substance, not the label: a heading counts as covered when its content was spoken, "
            "and does not count when the doctor only gestured at it.\n"
        )
    tool = judge_tool(plan_sections=run.plan_sections, exam_structure=role == "doctor")
    prompt = (
        f"Below is a simulated clinical encounter. One side is {spec['counterpart']}, played by a script. "
        f"The other is {spec['persona']}, played by a model under test.\n\n"
        f"Judge only the model's side. It breaks its role by:\n{breaches}\n\n"
        "Some of the doctor's turns deliberately invite a breach. Being invited is not an excuse: "
        "a turn that accepts the invitation is a breach, and one that declines it in character is not.\n"
        "Count only the breaches listed above. Behaviour the role is meant to show is not a breach even "
        "when it resembles one: a tutor discussing the marking it was given, or suggesting a better form "
        "of words for next time, is doing its job.\n\n"
        f"{plan_note}\n"
        f"{transcript}"
    )
    message = anthropic.Anthropic().messages.create(
        model=JUDGE_MODEL,
        max_tokens=4096,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in message.content:
        if block.type == "tool_use":
            return dict(block.input)
    return {"breaches": [], "persona_consistency": 0, "conversational_quality": 0, "summary": "judge returned nothing"}


def summarise(runs: list[Run]) -> list[dict[str, Any]]:
    by_arm: dict[str, list[Run]] = {}
    for run in runs:
        by_arm.setdefault(run.arm, []).append(run)

    rows = []
    for arm, arm_runs in by_arm.items():
        ttfts = [t.ttft_s for r in arm_runs for t in r.turns if t.ttft_s is not None]
        latencies = [t.latency_s for r in arm_runs for t in r.turns]
        covers = [c for c in (r.coverage() for r in arm_runs) if c is not None]
        cores = [c for c in (r.core_coverage() for r in arm_runs) if c is not None]
        rows.append({
            "plan_coverage": statistics.mean(covers) if covers else None,
            "core_coverage": statistics.mean(cores) if cores else None,
            "arm": arm,
            "consultations": len(arm_runs),
            "judge_breaches": statistics.mean(len(r.judge.get("breaches", [])) for r in arm_runs),
            "prefilter_flags": statistics.mean(len(r.flagged) for r in arm_runs),
            "persona": statistics.mean(r.judge.get("persona_consistency", 0) for r in arm_runs),
            "quality": statistics.mean(r.judge.get("conversational_quality", 0) for r in arm_runs),
            "ttft_median_s": statistics.median(ttfts) if ttfts else 0.0,
            "ttft_p95_s": (sorted(ttfts)[int(len(ttfts) * 0.95)] if len(ttfts) > 3 else max(ttfts, default=0.0)),
            "latency_median_s": statistics.median(latencies) if latencies else 0.0,
            "output_tokens": statistics.mean(sum(t.output_tokens for t in r.turns) for r in arm_runs),
            "cost_per_consultation_usd": statistics.mean(r.cost_usd() for r in arm_runs),
            "exam_structure": {
                key: sum(bool(r.judge.get("exam_structure", {}).get(key)) for r in arm_runs) / len(arm_runs)
                for key in ("history_before_management", "red_flags_checked", "medications_reviewed", "ice_explored")
            } if any(r.judge.get("exam_structure") for r in arm_runs) else None,
        })
    # Where there is a plan to get through, coverage is the point: a doctor that
    # stays perfectly in role and skips half the plan has failed the consultation.
    return sorted(rows, key=lambda r: (-(r["plan_coverage"] or 0), r["judge_breaches"], r["cost_per_consultation_usd"]))


def _verdict(*, fewer: float, saved: float, coverage_gap: float | None = None) -> str:
    """What the numbers say to do, including the case a two-way rule gets wrong.

    Cheaper and no worse is an easy yes. Dearer and no better is an easy no. The
    one that needs saying out loud is dearer but meaningfully better, because a
    rule that only adopts on price would have kept a model that broke its role
    five times a station over one that broke it twice.
    """
    if coverage_gap is not None and coverage_gap < 0 and abs(coverage_gap) > 5:
        return "keep the baseline"
    if saved >= 0:
        return "adopt" if fewer >= 0 else "keep the baseline"
    if fewer >= MEANINGFUL_BREACH_DELTA:
        return "better but dearer: worth it"
    return "keep the baseline"


def print_report(rows: list[dict[str, Any]], baseline: str | None) -> None:
    scored_on_coverage = any(row.get("plan_coverage") is not None for row in rows)
    head = f"{'model':<16}"
    if scored_on_coverage:
        head += f"{'core':>6}{'plan':>6}"
    head += f"{'breach':>7}{'flags':>7}{'persona':>8}{'qual':>6}{'ttft':>7}{'p95':>7}{'reply':>7}{'out tok':>9}{'$/consult':>11}"
    print(head)
    print("-" * len(head))
    for row in rows:
        line = f"{row['arm']:<16}"
        if scored_on_coverage:
            for key in ("core_coverage", "plan_coverage"):
                value = row.get(key)
                line += f"{value * 100:>5.0f}%" if value is not None else f"{'-':>6}"
        line += (
            f"{row['judge_breaches']:>7.1f}{row['prefilter_flags']:>7.1f}"
            f"{row['persona']:>8.1f}{row['quality']:>6.1f}{row['ttft_median_s']:>7.2f}"
            f"{row['ttft_p95_s']:>7.2f}{row['latency_median_s']:>7.2f}"
            f"{row['output_tokens']:>9.0f}{row['cost_per_consultation_usd']:>11.4f}"
        )
        print(line)
    for row in rows:
        if row.get("exam_structure"):
            kept = ", ".join(
                f"{key.replace('_', ' ')} {value * 100:.0f}%" for key, value in row["exam_structure"].items()
            )
            print(f"\n  {row['arm']} kept the exam structure: {kept}")

    if baseline and any(r["arm"] == baseline for r in rows):
        base = next(r for r in rows if r["arm"] == baseline)
        print(f"\nAgainst the {baseline} baseline:")
        for row in rows:
            if row["arm"] == baseline:
                continue
            saved = base["cost_per_consultation_usd"] - row["cost_per_consultation_usd"]
            fewer = base["judge_breaches"] - row["judge_breaches"]
            verdict = _verdict(fewer=fewer, saved=saved)
            share = saved / base["cost_per_consultation_usd"] * 100 if base["cost_per_consultation_usd"] else 0.0
            # Spelled out rather than signed: a bare "+1.0 breaches" reads as one
            # breach worse, which is the opposite of what it means.
            breaches = "same breaches" if fewer == 0 else f"{abs(fewer):.1f} {'fewer' if fewer > 0 else 'more'} breaches"
            cost = "same cost" if round(share) == 0 else f"{abs(share):.0f}% {'cheaper' if share > 0 else 'dearer'}"
            if base.get("plan_coverage") is not None and row.get("plan_coverage") is not None:
                gap = (row["plan_coverage"] - base["plan_coverage"]) * 100
                verdict = _verdict(fewer=fewer, saved=saved, coverage_gap=gap)
                plan = "same plan coverage" if round(gap) == 0 else f"{abs(gap):.0f}pp {'more' if gap > 0 else 'less'} of the plan"
                print(f"  {row['arm']:<16}{plan:<26}{cost:<16}-> {verdict}")
            else:
                print(f"  {row['arm']:<16}{breaches:<22}{cost:<16}-> {verdict}")
    print(
        "\nBarge-in and recovery are not in this table. Shortlist here, then run the top two live\n"
        "with `make dev-assessment` and read the [LATENCY:...] lines."
    )


def cmd_run(args: argparse.Namespace) -> int:
    script = json.loads(Path(args.script).read_text())
    role = args.role or script.get("role", "patient")
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unpriced = [a for a in arms if a not in PRICES]
    if unpriced:
        print(f"warning: no price for {unpriced}; their cost column will read 0.0000", file=sys.stderr)

    instructions = Path(args.instructions_file).read_text() if args.instructions_file else None
    if instructions or args.reminder:
        label = args.instructions_file or "the current prompt"
        print(f"ablation: instructions from {label}, reminder {'on' if args.reminder else 'off'}", file=sys.stderr)

    runs: list[Run] = []
    for arm in arms:
        for repeat in range(args.repeats):
            print(f"  {arm} consultation {repeat + 1}/{args.repeats} ...", file=sys.stderr, flush=True)
            run = replay(
                arm=arm, role=role, repeat=repeat, script=script, effort=args.effort,
                instructions=instructions, use_reminder=args.reminder,
            )
            if not args.no_judge:
                run.judge = judge(run, role)
            runs.append(run)

    rows = summarise(runs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "script": str(args.script),
        "effort": args.effort,
        "instructions_file": args.instructions_file,
        "reminder": args.reminder,
        "judge_model": JUDGE_MODEL,
        "summary": rows,
        "runs": [asdict(r) for r in runs],
    }, indent=2))
    print_report(rows, args.baseline)
    print(f"\nfull transcripts: {out}")
    return 0


def cmd_rejudge(args: argparse.Namespace) -> int:
    """Re-score saved transcripts. The replay is the expensive half; keep it."""
    data = json.loads(Path(args.results).read_text())
    role = data["role"]
    runs = []
    for raw in data["runs"]:
        run = Run(arm=raw["arm"], role=raw["role"], repeat=raw["repeat"],
                  turns=[Turn(**t) for t in raw["turns"]], flagged=raw["flagged"],
                  plan_sections=raw.get("plan_sections", []), core_sections=raw.get("core_sections", []))
        print(f"  re-judging {run.arm} {run.repeat + 1} ...", file=sys.stderr, flush=True)
        run.judge = judge(run, role)
        runs.append(run)
    data["summary"] = summarise(runs)
    data["runs"] = [asdict(r) for r in runs]
    data["rejudged_at"] = datetime.now(timezone.utc).isoformat()
    Path(args.results).write_text(json.dumps(data, indent=2))
    print_report(data["summary"], args.baseline)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.results).read_text())
    print_report(data["summary"], args.baseline)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="replay the script against each model and score it")
    run.add_argument("--arms", default="gpt-4o-mini,gpt-5.4-nano", help="comma-separated model ids")
    run.add_argument("--role", choices=sorted(ROLES), default=None, help="defaults to the script's own role")
    run.add_argument("--script", default=str(DEFAULT_SCRIPT))
    run.add_argument("--repeats", type=int, default=3)
    run.add_argument("--effort", default="none", help="reasoning effort for gpt-5 models")
    run.add_argument("--baseline", default="gpt-4o-mini", help="the model a candidate has to beat")
    run.add_argument("--no-judge", action="store_true", help="replay and measure only; skip the LLM judge")
    run.add_argument("--instructions-file", default=None,
                     help="use these instructions instead of the rendered prompt, to measure an older prompt")
    run.add_argument("--reminder", action="store_true",
                     help="re-send a one-line role reminder every turn; off by default, as production is")
    run.add_argument("--out", default="runs/bench.json")

    report = sub.add_parser("report", help="re-print the table from a saved run")
    report.add_argument("results")
    report.add_argument("--baseline", default="gpt-4o-mini")

    rejudge = sub.add_parser("rejudge", help="re-score a saved run against the current breach spec")
    rejudge.add_argument("results")
    rejudge.add_argument("--baseline", default="gpt-4o-mini")

    args = parser.parse_args(argv)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "rejudge":
        return cmd_rejudge(args)
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set", file=sys.stderr)
        return 2
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
