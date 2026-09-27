"""How long a debrief runs, and what the tutor is told as the time passes.

The consultation clock's twin, reworded for a debrief. Without it the tutor
paces by turn count and wraps up about two thirds of the way through: it asked
for takeaways, or offered to stop, around the sixth exchange of eighteen in
``scripts/debrief_bench.py``, and the plan's later sections went unreached.

Like ``consultation_pacing``, every word the model reads about time is written
here, and the worker receives only seconds and finished sentences. The prompt's
``<pacing>`` block and the payload the worker runs come from the same numbers,
so they cannot disagree.
"""

from __future__ import annotations

from typing import Any

from .consultation_pacing import _note, human_duration

__all__ = ["DEBRIEF_PACING_BLOCK", "DEBRIEF_SECONDS", "debrief_pacing_payload"]

# Ten minutes, the length the debrief was designed and benchmarked for.
DEBRIEF_SECONDS = 600

# Where the plan walk-through ends and the takeaways begin. Two minutes is enough
# to ask what they will take away, add the one thing they left out, and close.
_CLOSE_STARTS_AT = 480

# (until_seconds, label), in order: what check_time says the tutor should be doing.
_PHASES: tuple[tuple[int, str], ...] = (
    (90, "hearing how it felt and agreeing where to start"),
    (_CLOSE_STARTS_AT, "working through the management plan together"),
    (DEBRIEF_SECONDS, "what they will take away, and the close"),
)

# (at_seconds, note body); each body is wrapped by the consultation clock's _note,
# so the tutor reads the same "never faster, never out loud" clause the doctor does.
_MARKS: tuple[tuple[int, str], ...] = (
    (
        150,
        "About 2 min 30 sec have gone, a quarter of this debrief, and about 7 min 30 sec remain. "
        "You should be into the management plan by now, starting from the part they chose. If you are "
        "still on how it felt, move to the plan through the moment they found hardest. There is no "
        "credit for finishing early.",
    ),
    (
        300,
        "Half the debrief has gone, and about 5 min remain. Think which parts of the plan you have not "
        "reached. If the safety netting, the follow-up or the treatment are among them, bring one in next, "
        "through something the doctor said. If you have covered most of the plan, go deeper into the part "
        "they were least sure about, or offer to practise the moment they found hard.",
    ),
    (
        _CLOSE_STARTS_AT,
        "About 2 min remain: enough to finish the part you are on and close, and no more. Do not open a new "
        "part of the plan or start a role-play. Ask what they will take away, add the one thing from the plan "
        "you most want them to remember if they leave it out, and close warmly.",
    ),
    (
        DEBRIEF_SECONDS,
        "You are at the end of the time set aside for this debrief. Finish the point you are on "
        "and close warmly. Do not start anything new, and do not cut the doctor off mid-sentence.",
    ),
)

# Modelled on athena_doctor's <pacing> block, and kept as short for the same
# reason: every rule added to an over-constrained prompt was measured to raise
# breaches.
DEBRIEF_PACING_BLOCK = (
    "<pacing>\n"
    f"This debrief is about {human_duration(DEBRIEF_SECONDS)} long. A bracketed [Notice: ...] will arrive "
    "from time to time telling you where you are in that time, and you can call check_time yourself if you "
    "are unsure. Both are for you alone: never read one out, never mention the clock, and never tell the "
    "doctor how long is left or that you are short of time.\n"
    "Until a notice tells you otherwise, assume you have this time and that you are meant to use all of it. "
    "Do not close until a notice, or check_time, tells you the time for takeaways and the close has come. "
    "Closing early is a failure here, not efficiency.\n"
    "A notice saying you are behind changes which parts of the plan you leave out, never how fast you speak. "
    "Keep the safety netting, the follow-up and the treatment, and leave the optional parts out.\n"
    "</pacing>"
)


def debrief_pacing_payload() -> dict[str, Any]:
    """The debrief's clock as data the worker can run, in ``consultation_pacing_payload``'s shape.

    Absolute marks in seconds, each with its sentence already written, and the
    phase labels the time tool reads back. JSON-able: it crosses HTTP.
    """
    return {
        "total_seconds": DEBRIEF_SECONDS,
        "marks": [{"at_seconds": at_seconds, "note": _note(body)} for at_seconds, body in _MARKS],
        "phases": [{"until_seconds": until_seconds, "label": label} for until_seconds, label in _PHASES],
    }
