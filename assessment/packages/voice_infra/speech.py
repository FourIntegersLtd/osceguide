"""Speech and language stacks for a voice session, chosen by role not product.

``build_stt`` is Deepgram direct (LiveKit Inference STT counts against a small
shared slot pool). ``build_llm`` and ``build_tts`` take the interaction role:
the simulated *patient* (gendered voice, cheaper primary model) or the
*tutor* voice used for debriefs (shared assistant voice, stronger model).
"""

from __future__ import annotations

from typing import Literal

from livekit.agents import llm, tts
from livekit.plugins import anthropic, cartesia, deepgram, openai
from livekit.plugins.deepgram import tts as deepgram_tts

Role = Literal["patient", "tutor"]
Gender = Literal["Female", "Male"]

TUTOR_VOICE = "marin"
TUTOR_TTS_MODEL = "gpt-4o-mini-tts"
CARTESIA_FEMALE_VOICE_ID = "794f9389-aac1-45b6-b726-9d9369183238"
CARTESIA_MALE_VOICE_ID = "95856005-0332-41b0-935f-352e296aa0df"


def build_stt() -> deepgram.STT:
    return deepgram.STT(model="nova-3-medical", language="en", punctuate=True, interim_results=True)


def build_llm(role: Role) -> llm.LLM:
    """Primary model by role, with a shared Anthropic fallback."""
    fallback = anthropic.LLM(model="claude-haiku-4-5", temperature=0.8)
    primary = openai.LLM(model="gpt-4o" if role == "tutor" else "gpt-4o-mini")
    return llm.FallbackAdapter([primary, fallback])


def _tutor_openai() -> tts.TTS:
    return openai.TTS(
        model=TUTOR_TTS_MODEL,
        voice=TUTOR_VOICE,
        instructions="Speak as Athena, a warm, confident and concise clinical education assistant.",
    )


def build_tts(role: Role, gender: Gender = "Female") -> tts.TTS:
    """Deepgram → OpenAI → Cartesia. Tutor uses the shared voice; patient is gendered."""
    if role == "tutor":
        return tts.FallbackAdapter([
            deepgram_tts.TTS(model="aura-2-athena-en"),
            _tutor_openai(),
            cartesia.TTS(voice=CARTESIA_FEMALE_VOICE_ID),
        ])
    female = gender == "Female"
    return tts.FallbackAdapter([
        deepgram_tts.TTS(model="aura-2-athena-en" if female else "aura-2-hermes-en"),
        _tutor_openai(),
        cartesia.TTS(voice=CARTESIA_FEMALE_VOICE_ID if female else CARTESIA_MALE_VOICE_ID),
    ])
