"""GPT-Live (speech-to-speech) construction shared by voice workers."""

from __future__ import annotations

from livekit.agents import vad
from livekit.plugins import silero
from livekit.plugins.openai.realtime import GPTLiveModel

from .speech import TUTOR_VOICE

GPT_LIVE_MODEL = "gpt-live-1"
GPT_LIVE_RESPONSES_MODEL = "gpt-5.6-luna"


def build_gpt_live_model(*, backend_instructions: str) -> GPTLiveModel:
    return GPTLiveModel(
        model=GPT_LIVE_MODEL,
        voice=TUTOR_VOICE,
        responses_options={
            "model": GPT_LIVE_RESPONSES_MODEL,
            "instructions": backend_instructions,
            "parallel_tool_calls": False,
            "reasoning": {"effort": "medium"},
            "text": {"verbosity": "low"},
        },
    )


def build_gpt_live_vad() -> vad.VAD:
    """GPT-Live needs an explicit VAD for local playback interruption."""
    return silero.VAD.load(
        min_speech_duration=0.1,
        min_silence_duration=0.45,
        prefix_padding_duration=0.3,
        activation_threshold=0.5,
    )
