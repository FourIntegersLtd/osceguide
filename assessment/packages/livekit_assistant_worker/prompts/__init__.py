"""Pure prompt templates the assistant worker renders itself."""

from .gpt_live import GPTLiveInstructions, build_help_instructions, build_onboarding_instructions, build_onboarding_scene_update
from .greetings import greeting_for
from .help import HelpInstructions, instruction_header
from .onboarding import OnboardingInstructions

__all__ = [
    "GPTLiveInstructions",
    "HelpInstructions",
    "OnboardingInstructions",
    "build_help_instructions",
    "build_onboarding_instructions",
    "build_onboarding_scene_update",
    "greeting_for",
    "instruction_header",
]
