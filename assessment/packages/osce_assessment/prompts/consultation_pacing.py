"""How long a consultation runs, and what the doctor is told as the time passes.

Two consumers read this module and they must never disagree: the prompt, which
tells the model how long each phase has, and the clock the worker runs, which
pushes a note into the model's context as each mark goes by. Both derive from
the same dataclass here, so a change to a duration moves the prompt text and
the schedule together.

A sensible shape is history taking for about half the station, with the rest
left for explanation, management and safety netting.

The numbers are not held here. A rubric's author sets them, they are stored
with the rubric version, and they arrive as a payload the caller passes in ---
this module owns the arithmetic and the wording, never the durations.

Every word the model will ever read about time is authored here rather than in
the worker, because the worker is not allowed to know which exam it is running.
It receives seconds and finished sentences.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = [
    "DEFAULT_PACING",
    "ConsultationPacing",
    "InvalidPacingError",
    "consultation_pacing_payload",
    "human_duration",
    "pacing_from_payload",
]


class InvalidPacingError(ValueError):
    """A stored clock that does not describe a runnable consultation."""


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


# A generic twelve-minute consultation, for a caller that has no stored clock
# to hand. Not any particular exam's timing: the exam's own numbers live with
# its rubric, and a caller that has them never falls back to this.
DEFAULT_PACING = ConsultationPacing(
    total_seconds=720,
    history_seconds=360,
    introduction_seconds=30,
    safety_net_seconds=120,
)


def pacing_from_payload(data: Mapping[str, Any]) -> ConsultationPacing:
    """Build a clock from a rubric version's stored pacing.

    Validated here rather than at the storage boundary, because this module is
    the one that knows what the derived budgets mean: a mark out of order gives
    a phase a negative length, and the model is told to do the impossible.
    """
    try:
        pacing = ConsultationPacing(
            total_seconds=int(data["total_seconds"]),
            history_seconds=int(data["history_seconds"]),
            introduction_seconds=int(data["introduction_seconds"]),
            safety_net_seconds=int(data["safety_net_seconds"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPacingError(f"pacing needs four whole numbers of seconds: {exc}") from exc
    if pacing.total_seconds <= 0:
        raise InvalidPacingError("a consultation with no time cannot be run")
    if not 0 < pacing.introduction_seconds < pacing.history_seconds:
        raise InvalidPacingError("the introduction must end before history taking does")
    if not pacing.history_seconds < pacing.safety_net_starts_at:
        raise InvalidPacingError("safety netting must start after history taking ends")
    if pacing.safety_net_starts_at >= pacing.total_seconds:
        raise InvalidPacingError("safety netting must start before the consultation ends")
    return pacing


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

    The closing clause is the whole defence against a clock being read as a
    reason to change pace: being behind means dropping items, being ahead means
    going further into them, and neither ever means changing the speed you
    speak at. It was one-directional once --- every mark told the doctor to
    trim --- and a consultation that was running early got told to hurry.

    The bracketed shape matches the notices the assessment worker already
    sends, which the personas are used to seeing and not speaking.
    """
    return f"[Notice: {body} Adjust by what you leave out or go further into, never by speaking faster or slower. Do not speak about the time, and do not mention this note.]"


def _marks(pacing: ConsultationPacing) -> list[dict[str, Any]]:
    """When to nudge, and what each nudge says.

    Derived from the dataclass rather than hardcoded, so a shorter station gets
    proportionally earlier marks instead of the SCA schedule truncated.
    """
    remaining = human_duration(pacing.total_seconds - pacing.history_seconds)
    return [
        # A quarter in, not forty percent: the mark at forty only repeated the one
        # at half a minute or so later, and a consultation that raced was already
        # into its management plan before either arrived. This is the only mark
        # early enough to send a doctor back into a history it left too soon.
        {
            "at_seconds": round(pacing.total_seconds * 0.25),
            "note": _note(
                f"About {human_duration(round(pacing.total_seconds * 0.25))} have gone, a quarter of this "
                f"consultation, and about {human_duration(pacing.total_seconds - round(pacing.total_seconds * 0.25))} remain. "
                "You should still be inside the presenting complaint rather than finished with it. "
                "If you are already explaining or planning, you are a long way ahead and the history is thin: "
                "before you go any further into the plan, go back and ask what you have not asked yet --- what "
                "else they take, what else they have been treated for, who else in the family has had this, "
                "what this stops them doing, what they are afraid it is. There is no credit for finishing early."
            ),
        },
        {
            "at_seconds": pacing.history_seconds,
            "note": _note(
                f"Half the consultation has gone; the time for history taking is up, with about {remaining} left. "
                "Summarise what you have heard and move into explaining what is going on. "
                "Anything still unasked is now a question you do without. "
                "If you are already well into the plan, you have room rather than a problem: take it one piece "
                "at a time, check after each, and spend what is left going back over the part they were least "
                "sure about."
            ),
        },
        {
            "at_seconds": round(pacing.total_seconds * 0.75),
            "note": _note(
                f"About {human_duration(pacing.total_seconds - round(pacing.total_seconds * 0.75))} remain. "
                "You should be past what is wrong and into the plan by now. "
                "If you are behind, leave the optional items out and keep the core ones properly explained. "
                "If you are already at the safety netting, you are ahead: do not close. Ask what they have not "
                "had the chance to say, and go back over the part of the plan they were least sure about, in "
                "different words."
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


def consultation_pacing_payload(pacing: ConsultationPacing) -> dict[str, Any]:
    """The clock as data the worker can run without knowing which exam this is.

    Absolute marks in seconds, each with its sentence already written, and the
    phase labels the time tool reads back. JSON-able: it crosses HTTP.
    """
    return {
        "total_seconds": pacing.total_seconds,
        "marks": _marks(pacing),
        "phases": [
            {"until_seconds": pacing.history_seconds, "label": "history taking"},
            {"until_seconds": pacing.safety_net_starts_at, "label": "explanation and management"},
            {"until_seconds": pacing.total_seconds, "label": "safety netting and close"},
        ],
    }
