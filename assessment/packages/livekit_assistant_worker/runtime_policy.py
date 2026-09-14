"""Choose the voice runtime before an AgentSession is created."""

from __future__ import annotations

import os
from enum import StrEnum


class VoiceRuntime(StrEnum):
    PIPELINE = "pipeline"
    GPT_LIVE = "gpt-live"


def gpt_live_enabled() -> bool:
    """GPT-Live is available when the worker has an OpenAI API key."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def select_voice_runtime(*, worker_type: str, voice_help_intent: str | None, screen_ui_guidance: bool) -> VoiceRuntime:
    """Use GPT-Live only for FAQ Help when credentials are present."""
    if not gpt_live_enabled():
        return VoiceRuntime.PIPELINE
    if worker_type == "help" and voice_help_intent == "faq" and not screen_ui_guidance:
        return VoiceRuntime.GPT_LIVE
    return VoiceRuntime.PIPELINE
