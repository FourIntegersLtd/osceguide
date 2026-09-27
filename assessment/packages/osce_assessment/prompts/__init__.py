"""Platform default prompts and the formatters that render them.

Prompt *text* lives beside this file as data (``*.txt``); nothing here decides
which text applies to whom. Marking instructions are not shipped at all: they
are written by whoever authors a rubric and travel on the framework. What is
left here is the wording every persona shares and the formatters that turn a
stored station document into finished instructions.

Every live persona is built from the shared blocks in ``_blocks`` so the role
wording cannot drift apart between them, and opens by naming the role it is
cast in. A per-turn reminder was tried on top of that and measured on two
personas: it bought nothing on the simulated patient and made the consulting
doctor worse, so the role lives in the prompt alone.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

from .athena_doctor import AthenaDoctorFormatter
from .consultation_pacing import (
    DEFAULT_PACING,
    ConsultationPacing,
    InvalidPacingError,
    consultation_pacing_payload,
    pacing_from_payload,
)
from .cv import format_structured_cv_for_llm
from .debrief_pacing import DEBRIEF_PACING_BLOCK, DEBRIEF_SECONDS, debrief_pacing_payload
from .dashboard_feedback import DashboardFeedbackPromptFormatter
from .dashboard_tutor import DashboardTutorFormatter
from .debrief_feedback import (
    OrthoClinicalSkillFeedbackFormatter,
    OrthoCommunicationSkillFeedbackFormatter,
    OrthoFeedbackFormatter,
    OrthoPortfolioSkillFeedbackFormatter,
    OrthoPrioritisationSkillFeedbackFormatter,
    PlabFeedbackFormatter,
    ScaFeedbackFormatter,
)
from .debrief_management_plan import ManagementPlanFormatter
from .debrief_prompt import DebriefPromptFormatter
from .debrief_transcript import TranscriptFormatter
from .greetings import DEBRIEF_GREETING, EXAMINER_GREETINGS, PATIENT_GREETINGS
from .station import StationPromptFormatter, create_station_prompt, station_examiner_context

USER_PROMPT_TEMPLATE_ID = "feedback_evaluation_v1"

class UnknownPromptError(LookupError):
    """Raised for a prompt id with no text file beside this module."""


@lru_cache(maxsize=None)
def prompt_text(prompt_id: str) -> str:
    """The verbatim text of a prompt shipped with the engine."""
    ref = resources.files(__name__).joinpath(f"{prompt_id}.txt")
    if not ref.is_file():
        raise UnknownPromptError(f"no prompt text for {prompt_id!r}; known: {available_prompt_ids()}")
    return ref.read_text(encoding="utf-8")


def available_prompt_ids() -> tuple[str, ...]:
    return tuple(sorted(p.name[:-4] for p in resources.files(__name__).iterdir() if p.name.endswith(".txt")))


def system_prompt(prompt_id: str) -> str:
    return prompt_text(prompt_id)


def render_user_prompt(*, station_name: str, transcript: str) -> str:
    """The evaluation user prompt: the station name and the tagged transcript."""
    return prompt_text(USER_PROMPT_TEMPLATE_ID).format(station_name=station_name, transcript=transcript)


__all__ = [
    "DEBRIEF_GREETING",
    "EXAMINER_GREETINGS",
    "PATIENT_GREETINGS",
    "USER_PROMPT_TEMPLATE_ID",
    "AthenaDoctorFormatter",
    "ConsultationPacing",
    "DEFAULT_PACING",
    "InvalidPacingError",
    "consultation_pacing_payload",
    "DEBRIEF_PACING_BLOCK",
    "DEBRIEF_SECONDS",
    "debrief_pacing_payload",
    "pacing_from_payload",
    "DashboardFeedbackPromptFormatter",
    "DashboardTutorFormatter",
    "DebriefPromptFormatter",
    "ManagementPlanFormatter",
    "StationPromptFormatter",
    "OrthoClinicalSkillFeedbackFormatter",
    "OrthoCommunicationSkillFeedbackFormatter",
    "OrthoFeedbackFormatter",
    "OrthoPortfolioSkillFeedbackFormatter",
    "OrthoPrioritisationSkillFeedbackFormatter",
    "PlabFeedbackFormatter",
    "ScaFeedbackFormatter",
    "TranscriptFormatter",
    "UnknownPromptError",
    "available_prompt_ids",
    "create_station_prompt",
    "format_structured_cv_for_llm",
    "station_examiner_context",
    "prompt_text",
    "render_user_prompt",
    "system_prompt",
]
