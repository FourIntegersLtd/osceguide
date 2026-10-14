"""Choose the voice runtime before an AgentSession is created."""

from __future__ import annotations

import os
from enum import StrEnum

from .modes import is_faq_help, mode_profile


class VoiceRuntime(StrEnum):
    """The two ways a voice session can run: separate speech models, or one speech-to-speech model."""

    PIPELINE = "pipeline"
    GPT_LIVE = "gpt-live"


def gpt_live_enabled() -> bool:
    """GPT-Live runs only when ASSISTANT_GPT_LIVE_ENABLED=1 and the worker has an OpenAI API key."""
    # Off by default: every assistant session runs the pipeline (Athena on Deepgram first); set the variable to bring GPT-Live back.
    return os.getenv("ASSISTANT_GPT_LIVE_ENABLED", "").strip() == "1" and bool(os.getenv("OPENAI_API_KEY", "").strip())


def select_voice_runtime(*, worker_type: str, voice_help_intent: str | None, screen_ui_guidance: bool, gpt_live_offered: bool = True) -> VoiceRuntime:
    """Speech-to-speech only for voice-only FAQ help on an eligible mode, when the backend
    supplied speech-to-speech instructions and credentials are present."""
    if not gpt_live_enabled() or not gpt_live_offered:
        return VoiceRuntime.PIPELINE
    if mode_profile(worker_type).gpt_live_eligible and is_faq_help(worker_type, voice_help_intent) and not screen_ui_guidance:
        return VoiceRuntime.GPT_LIVE
    return VoiceRuntime.PIPELINE
