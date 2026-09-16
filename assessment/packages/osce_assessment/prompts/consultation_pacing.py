"""How long a consultation runs, and what the doctor is told as the time passes.

Two consumers read this module and they must never disagree: the prompt, which
tells the model how long each phase has, and the clock the worker runs, which
pushes a note into the model's context as each mark goes by. Both derive from
the same dataclass here, so a change to a duration moves the prompt text and
the schedule together.

The numbers mirror the station lengths the consumers already use --- the
``*_SIMULATION_TIMER_DURATION`` constants in the frontend and the timing table
in the other backend. History gets half the station; the rest is explanation,
management and safety netting.

Keyed by framework id, which is the engine's vocabulary for an exam. Callers
still holding a legacy product string translate it once through
``compat.framework_id_for_app_type`` before calling in.

Every word the model will ever read about time is authored here rather than in
the worker, because the worker is not allowed to know which exam it is running.
It receives seconds and finished sentences.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "DEFAULT_FRAMEWORK_ID",
    "PACING_BY_FRAMEWORK_ID",
    "ConsultationPacing",
    "consultation_pacing_payload",
    "human_duration",
    "pacing_for_framework",
]


@dataclass(frozen=True)
class ConsultationPacing:
    """One station's clock, in seconds from the moment the consultation opens.

    ``history_seconds`` is the mark where history should be over, counted from
    the start and so including the introduction --- it is a point on the clock,
    not a budget. The budgets the prompt quotes are the derived properties.
    """

    total_seconds: int
    history_seconds: int
    introduction_seconds: int
    safety_net_seconds: int

    @property
    def history_talk_seconds(self) -> int:
        """History taking proper, once the introduction is out of the way."""
        return self.history_seconds - self.introduction_seconds

    @property
    def safety_net_starts_at(self) -> int:
        return self.total_seconds - self.safety_net_seconds

    @property
    def management_seconds(self) -> int:
        """What is left for explanation and the plan: the longest stretch."""
        return self.safety_net_starts_at - self.history_seconds


PACING_BY_FRAMEWORK_ID: dict[str, ConsultationPacing] = {
    "sca-rcgp-v1": ConsultationPacing(total_seconds=720, history_seconds=360, introduction_seconds=30, safety_net_seconds=120),
    "plab2-gmc-v1": ConsultationPacing(total_seconds=480, history_seconds=240, introduction_seconds=20, safety_net_seconds=80),
    "casc-rcpsych-v1": ConsultationPacing(total_seconds=480, history_seconds=240, introduction_seconds=20, safety_net_seconds=80),
    "ortho-frcs-v1": ConsultationPacing(total_seconds=600, history_seconds=300, introduction_seconds=30, safety_net_seconds=100),
}

DEFAULT_FRAMEWORK_ID = "sca-rcgp-v1"


def pacing_for_framework(framework_id: str | None) -> ConsultationPacing:
    """The clock for one framework; the longest station when the id is unknown.

    An unrecognised id gets the most generous clock rather than the meanest:
    a consultation given too much time reads as unhurried, one given too little
    reads as the rush this module exists to fix.
    """
    return PACING_BY_FRAMEWORK_ID.get((framework_id or "").strip().lower(), PACING_BY_FRAMEWORK_ID[DEFAULT_FRAMEWORK_ID])


def human_duration(seconds: int) -> str:
    """Said the way a person says it, because this goes into spoken-word prompts."""
    if seconds < 60:
        return f"{seconds} sec"
    minutes = seconds / 60
    if abs(minutes - round(minutes)) < 0.05:
        return f"{round(minutes)} min"
    return f"{minutes:.1f} min"


def _note(body: str) -> str:
    """A note the model reads and never repeats.

    The closing clause is the whole defence against a clock being read as
    permission to rush: falling behind means dropping items, never talking
    faster. The bracketed shape matches the notices the assessment worker
    already sends, which the personas are used to seeing and not speaking.
    """
    return f"[Notice: {body} Adjust by leaving things out, never by speaking faster or bundling turns together. Do not speak about the time, and do not mention this note.]"


def _marks(pacing: ConsultationPacing) -> list[dict[str, Any]]:
    """When to nudge, and what each nudge says.

    Derived from the dataclass rather than hardcoded, so a shorter station gets
    proportionally earlier marks instead of the SCA schedule truncated.
    """
    remaining = human_duration(pacing.total_seconds - pacing.history_seconds)
    return [
        {
            "at_seconds": round(pacing.total_seconds * 0.4),
            "note": _note(
                f"About {human_duration(round(pacing.total_seconds * 0.4))} of this consultation have gone and "
                f"about {human_duration(pacing.total_seconds - round(pacing.total_seconds * 0.4))} remain. "
                "If the presenting complaint is still wide open, start bringing the history towards a close."
            ),
        },
        {
            "at_seconds": pacing.history_seconds,
            "note": _note(
                f"Half the consultation has gone; the time for history taking is up, with about {remaining} left. "
                "Summarise what you have heard and move into explaining what is going on. "
                "Anything still unasked is now a question you do without."
            ),
        },
        {
            "at_seconds": round(pacing.total_seconds * 0.75),
            "note": _note(
                f"About {human_duration(pacing.total_seconds - round(pacing.total_seconds * 0.75))} remain. "
                "You should be past what is wrong and into the plan by now. "
                "If you are behind, leave the optional items out and keep the core ones properly explained."
            ),
        },
        {
            "at_seconds": pacing.safety_net_starts_at,
            "note": _note(
                f"About {human_duration(pacing.safety_net_seconds)} remain --- enough for the safety netting and "
                "the close, and no more. Move to what to watch for and what to do if things change, one action per turn."
            ),
        },
        {
            "at_seconds": pacing.total_seconds,
            "note": _note(
                "You are at the end of the time set aside for this consultation. "
                "Finish the point you are on and close warmly. Do not start anything new, "
                "and do not cut the patient off mid-sentence."
            ),
        },
    ]


def consultation_pacing_payload(framework_id: str | None) -> dict[str, Any]:
    """The clock as data the worker can run without knowing which exam this is.

    Absolute marks in seconds, each with its sentence already written, and the
    phase labels the time tool reads back. JSON-able: it crosses HTTP.
    """
    pacing = pacing_for_framework(framework_id)
    return {
        "total_seconds": pacing.total_seconds,
        "marks": _marks(pacing),
        "phases": [
            {"until_seconds": pacing.history_seconds, "label": "history taking"},
            {"until_seconds": pacing.safety_net_starts_at, "label": "explanation and management"},
            {"until_seconds": pacing.total_seconds, "label": "safety netting and close"},
        ],
    }
