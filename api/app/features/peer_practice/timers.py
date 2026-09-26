"""Per-exam phase lengths for peer practice (seconds)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseDurations:
    """How long, in seconds, each phase of a practice session runs for one exam."""

    preparation: int
    consultation: int
    debrief: int


_DEFAULT = PhaseDurations(preparation=180, consultation=720, debrief=900)

_BY_EXAM: dict[str, PhaseDurations] = {
    "sca": PhaseDurations(preparation=180, consultation=720, debrief=900),
    "plab": PhaseDurations(preparation=120, consultation=480, debrief=900),
    "casc": PhaseDurations(preparation=300, consultation=420, debrief=900),
    "ortho": PhaseDurations(preparation=300, consultation=600, debrief=900),
}


def durations_for(exam_code: str) -> PhaseDurations:
    """This exam's phase durations, or the default set for an exam with none of its own."""
    return _BY_EXAM.get(exam_code.lower(), _DEFAULT)
