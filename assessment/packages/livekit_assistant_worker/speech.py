"""Language and voice stacks for assistant sessions, by session type.

Help and onboarding run on Haiku (image blocks for the computer tool; cheap
voice); the consulting doctor uses the stronger model; everything else the
cheaper primary, all with a shared Anthropic fallback. Athena's voice is
Deepgram-first, except FAQ help which is OpenAI-first.
"""

from __future__ import annotations

from livekit.agents import llm, tts
from livekit.plugins import anthropic, cartesia, openai
from livekit.plugins.deepgram import tts as deepgram_tts
from voice_infra.speech import CARTESIA_FEMALE_VOICE_ID, TUTOR_TTS_MODEL, TUTOR_VOICE

HELP_FAQ_INTENT = "faq"


def build_assistant_llm(worker_type: str) -> llm.LLM:
    if worker_type in ("help", "onboarding"):
        return anthropic.LLM(model="claude-haiku-4-5")
    fallback = anthropic.LLM(model="claude-haiku-4-5", temperature=0.8)
    primary = openai.LLM(model="gpt-4o" if worker_type == "athena-doctor" else "gpt-4o-mini")
    return llm.FallbackAdapter([primary, fallback])


def _openai_athena() -> tts.TTS:
    return openai.TTS(
        model=TUTOR_TTS_MODEL,
        voice=TUTOR_VOICE,
        instructions="Speak as Athena, a warm, confident and concise clinical education assistant.",
    )


def build_assistant_tts(worker_type: str, *, voice_help_intent: str | None = None) -> tts.TTS:
    deepgram = deepgram_tts.TTS(model="aura-2-athena-en")
    cartesia_voice = cartesia.TTS(voice=CARTESIA_FEMALE_VOICE_ID)
    if worker_type == "help" and voice_help_intent == HELP_FAQ_INTENT:
        return tts.FallbackAdapter([_openai_athena(), deepgram, cartesia_voice])
    return tts.FallbackAdapter([deepgram, _openai_athena(), cartesia_voice])
