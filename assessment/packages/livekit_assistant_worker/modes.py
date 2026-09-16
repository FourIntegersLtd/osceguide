"""The session types this worker runs, and what each one needs, as one table.

The type names are the dispatching backend's vocabulary and arrive in the
bootstrap payload. Everything the worker decides per type (which model tier,
whether the transcript is kept, which event handlers and tools apply) is a
row here, so no other module needs a string comparison against a session
type. What the model is told is never decided here: instructions, greetings
and FAQ content all arrive rendered from the backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class WorkerType(StrEnum):
    HELP = "help"
    ONBOARDING = "onboarding"
    DASHBOARD = "dashboard"
    CONSULTING_DOCTOR = "consulting-doctor"


LlmTier = Literal["vision", "patient", "tutor"]

HELP_FAQ_INTENT = "faq"


@dataclass(frozen=True)
class ModeProfile:
    worker_type: WorkerType
    llm: LlmTier
    max_tool_steps: int
    keeps_transcript: bool = False
    gpt_live_eligible: bool = False
    ui_guidance: bool = False
    scene_updates: bool = False
    """The browser announces scene changes; the backend re-renders the instructions."""
    opens_with_generated_reply: bool = False
    """Open with a model-generated line instead of a fixed greeting."""
    paced: bool = False
    """The interaction runs against a clock the backend sent: time notices and a time tool apply."""


MODE_PROFILES: dict[WorkerType, ModeProfile] = {
    WorkerType.HELP: ModeProfile(WorkerType.HELP, llm="vision", max_tool_steps=10, keeps_transcript=True, gpt_live_eligible=True, ui_guidance=True),
    WorkerType.ONBOARDING: ModeProfile(WorkerType.ONBOARDING, llm="vision", max_tool_steps=10, scene_updates=True, opens_with_generated_reply=True),
    WorkerType.DASHBOARD: ModeProfile(WorkerType.DASHBOARD, llm="patient", max_tool_steps=5),
    WorkerType.CONSULTING_DOCTOR: ModeProfile(WorkerType.CONSULTING_DOCTOR, llm="tutor", max_tool_steps=5, paced=True),
}


def mode_profile(worker_type: WorkerType | str) -> ModeProfile:
    return MODE_PROFILES[WorkerType(worker_type)]


def is_faq_help(worker_type: WorkerType | str, voice_help_intent: str | None) -> bool:
    """Voice-only FAQ help: the one session shape that may run speech-to-speech."""
    return WorkerType(worker_type) is WorkerType.HELP and voice_help_intent == HELP_FAQ_INTENT
