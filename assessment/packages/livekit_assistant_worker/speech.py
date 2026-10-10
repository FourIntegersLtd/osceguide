"""The language model for an assistant session, by mode profile.

Delegates to ``voice_infra.speech`` so model ids are deployment settings shared
with every worker. The voice is not chosen here: every session type speaks with
the one tutor chain (``build_tts("tutor")``), so a session never changes voice.
"""

from __future__ import annotations

from livekit.agents import llm
from voice_infra.speech import build_llm, build_vision_llm

from .modes import ModeProfile


def build_assistant_llm(mode: ModeProfile) -> llm.LLM:
    return build_vision_llm() if mode.llm == "vision" else build_llm(mode.llm)
