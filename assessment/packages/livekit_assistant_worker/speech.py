"""Language and voice stacks for assistant sessions, by mode profile.

Delegates to ``voice_infra.speech`` so model ids and voices are deployment
settings shared with every worker. The only assistant-specific rule is that
voice-only FAQ help prefers the OpenAI voice.
"""

from __future__ import annotations

from livekit.agents import llm, tts
from voice_infra.speech import build_llm, build_tts, build_vision_llm

from .modes import ModeProfile, is_faq_help


def build_assistant_llm(mode: ModeProfile) -> llm.LLM:
    return build_vision_llm() if mode.llm == "vision" else build_llm(mode.llm)


def build_assistant_tts(mode: ModeProfile, *, voice_help_intent: str | None = None) -> tts.TTS:
    primary = "openai" if is_faq_help(mode.worker_type, voice_help_intent) else "deepgram"
    return build_tts("tutor", primary=primary)
