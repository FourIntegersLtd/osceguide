"""Speech and language stacks for a voice session, chosen by role not product.

``build_stt`` is Deepgram direct (LiveKit Inference STT counts against a small
shared slot pool). ``build_llm`` and ``build_tts`` take the interaction role:
the simulated *patient* (gendered voice, cheaper primary model) or the
*tutor* voice used for debriefs and assistants (shared voice, stronger
model). ``build_vision_llm`` is the image-capable model a session needs when
it looks at screenshots.

Model ids, voices and the spoken style are deployment settings: every field
of ``SpeechSettings`` can be overridden by ``VOICE_<FIELD>`` in the
environment, so a persona name or a model upgrade is configuration, never a
code change in this package.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, fields
from typing import Literal, get_type_hints

from livekit.agents import llm, tts
from livekit.plugins import anthropic, cartesia, deepgram, openai
from livekit.plugins.deepgram import tts as deepgram_tts

logger = logging.getLogger(__name__)

Role = Literal["patient", "tutor"]
Gender = Literal["Female", "Male"]
TtsProvider = Literal["deepgram", "openai"]

SETTINGS_ENV_PREFIX = "VOICE_"

# Kept as module constants because other packages and the GPT-Live model
# construction share them; they are the defaults ``SpeechSettings`` starts from.
TUTOR_VOICE = "marin"
TUTOR_TTS_MODEL = "gpt-4o-mini-tts"
CARTESIA_FEMALE_VOICE_ID = "794f9389-aac1-45b6-b726-9d9369183238"
CARTESIA_MALE_VOICE_ID = "95856005-0332-41b0-935f-352e296aa0df"


@dataclass(frozen=True)
class SpeechSettings:
    stt_model: str = "nova-3-medical"
    patient_llm: str = "gpt-4o-mini"
    tutor_llm: str = "gpt-4o"
    vision_llm: str = "claude-haiku-4-5"
    fallback_llm: str = "claude-haiku-4-5"
    fallback_temperature: float = 0.8
    tutor_tts_model: str = TUTOR_TTS_MODEL
    tutor_voice: str = TUTOR_VOICE
    tts_style: str = "Speak as a warm, confident and concise clinical education assistant."
    deepgram_tutor_voice: str = "aura-2-athena-en"
    deepgram_female_voice: str = "aura-2-athena-en"
    deepgram_male_voice: str = "aura-2-hermes-en"
    cartesia_female_voice: str = CARTESIA_FEMALE_VOICE_ID
    cartesia_male_voice: str = CARTESIA_MALE_VOICE_ID

    @classmethod
    def from_env(cls) -> "SpeechSettings":
        """Defaults, with any ``VOICE_<FIELD>`` environment variable applied."""
        types = get_type_hints(cls)
        overrides = {}
        for field in fields(cls):
            raw = (os.getenv(f"{SETTINGS_ENV_PREFIX}{field.name.upper()}") or "").strip()
            if not raw:
                continue
            try:
                overrides[field.name] = types[field.name](raw)
            except ValueError:
                logger.warning("ignoring %s%s=%r: not a %s", SETTINGS_ENV_PREFIX, field.name.upper(), raw, types[field.name].__name__)
        return cls(**overrides)


def build_stt(settings: SpeechSettings | None = None) -> deepgram.STT:
    settings = settings or SpeechSettings.from_env()
    return deepgram.STT(model=settings.stt_model, language="en", punctuate=True, interim_results=True)


def _fallback_llm(settings: SpeechSettings) -> llm.LLM:
    return anthropic.LLM(model=settings.fallback_llm, temperature=settings.fallback_temperature)


def build_llm(role: Role, settings: SpeechSettings | None = None) -> llm.LLM:
    """Primary model by role, with a shared Anthropic fallback."""
    settings = settings or SpeechSettings.from_env()
    primary = openai.LLM(model=settings.tutor_llm if role == "tutor" else settings.patient_llm)
    return llm.FallbackAdapter([primary, _fallback_llm(settings)])


def build_vision_llm(settings: SpeechSettings | None = None) -> llm.LLM:
    """The image-capable model, alone: tool results carry screenshots as image blocks."""
    settings = settings or SpeechSettings.from_env()
    return anthropic.LLM(model=settings.vision_llm)


def _openai_tts(settings: SpeechSettings) -> tts.TTS:
    return openai.TTS(model=settings.tutor_tts_model, voice=settings.tutor_voice, instructions=settings.tts_style)


def build_tts(
    role: Role,
    gender: Gender = "Female",
    *,
    primary: TtsProvider = "deepgram",
    settings: SpeechSettings | None = None,
) -> tts.TTS:
    """Deepgram and OpenAI in the order ``primary`` asks for, then Cartesia.

    The tutor uses the shared voice; the patient is gendered.
    """
    settings = settings or SpeechSettings.from_env()
    if role == "tutor":
        deepgram_voice, cartesia_voice = settings.deepgram_tutor_voice, settings.cartesia_female_voice
    elif gender == "Female":
        deepgram_voice, cartesia_voice = settings.deepgram_female_voice, settings.cartesia_female_voice
    else:
        deepgram_voice, cartesia_voice = settings.deepgram_male_voice, settings.cartesia_male_voice
    first_two = [deepgram_tts.TTS(model=deepgram_voice), _openai_tts(settings)]
    if primary == "openai":
        first_two.reverse()
    return tts.FallbackAdapter([*first_two, cartesia.TTS(voice=cartesia_voice)])
