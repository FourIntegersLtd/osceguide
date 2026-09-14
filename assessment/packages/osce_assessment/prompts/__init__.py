"""Platform default prompts and the formatters that render them.

Prompt *text* lives beside this file as data (``*.txt``); nothing here decides
which text applies to whom. A consumer picks a prompt id through its
``EvaluationPolicy`` or its own configuration, and the formatters turn a
scenario or a stored document into finished instructions.

The formatters were ported verbatim from the legacy workers; the snapshot tests
prove they render byte-identical output.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

from .cv import format_structured_cv_for_llm
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
from .library_station import ConversationPromptFormatter, OrthoPromptFormatter
from .org_station import OrgStationPromptFormatter, create_org_station_prompt

USER_PROMPT_TEMPLATE_ID = "feedback_evaluation_v1"

# The platform's default system prompt for each framework it publishes. A
# consumer's EvaluationPolicy may override this; the engine never picks by
# consumer. CASC has never had a prompt of its own and is marked with the SCA
# prompt, which is preserved here deliberately rather than silently.
_DEFAULT_SYSTEM_PROMPT_BY_FRAMEWORK: dict[str, str] = {
    "sca-rcgp-v1": "sca_feedback_assessment_v1",
    "plab2-gmc-v1": "plab_feedback_assessment_v1",
    "casc-rcpsych-v1": "sca_feedback_assessment_v1",
    "ortho-frcs-v1": "ortho_feedback_assessment_v1",
}


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


def default_system_prompt_id(framework_id: str) -> str:
    """The platform default prompt for a published framework."""
    try:
        return _DEFAULT_SYSTEM_PROMPT_BY_FRAMEWORK[framework_id]
    except KeyError:
        raise UnknownPromptError(
            f"no platform default prompt for framework {framework_id!r}; "
            f"known: {sorted(_DEFAULT_SYSTEM_PROMPT_BY_FRAMEWORK)}"
        ) from None


def render_user_prompt(*, station_name: str, transcript: str) -> str:
    """The evaluation user prompt: the station name and the tagged transcript."""
    return prompt_text(USER_PROMPT_TEMPLATE_ID).format(station_name=station_name, transcript=transcript)


__all__ = [
    "USER_PROMPT_TEMPLATE_ID",
    "ConversationPromptFormatter",
    "DebriefPromptFormatter",
    "ManagementPlanFormatter",
    "OrgStationPromptFormatter",
    "OrthoClinicalSkillFeedbackFormatter",
    "OrthoCommunicationSkillFeedbackFormatter",
    "OrthoFeedbackFormatter",
    "OrthoPortfolioSkillFeedbackFormatter",
    "OrthoPrioritisationSkillFeedbackFormatter",
    "OrthoPromptFormatter",
    "PlabFeedbackFormatter",
    "ScaFeedbackFormatter",
    "TranscriptFormatter",
    "UnknownPromptError",
    "available_prompt_ids",
    "create_org_station_prompt",
    "default_system_prompt_id",
    "format_structured_cv_for_llm",
    "prompt_text",
    "render_user_prompt",
    "system_prompt",
]
