"""Speech and language stacks for a voice session, chosen by role not product.

``build_stt`` is the speech-to-text model. ``build_llm`` and ``build_tts`` take
the interaction role: the simulated *patient* (gendered voice, cheaper primary
model) or the *tutor* voice used for debriefs and assistants (shared voice,
stronger model). ``build_vision_llm`` is the image-capable model a session needs
when it looks at screenshots. On LiveKit Cloud (``OSCE_LIVEKIT_HOSTING=cloud``)
every builder uses LiveKit Inference; our own workers use the provider plugins.

Model ids, voices and the spoken style are deployment settings: every field
of ``SpeechSettings`` can be overridden by ``VOICE_<FIELD>`` in the
environment, so a persona name or a model upgrade is configuration, never a
code change in this package. That is also what makes a model comparison
runnable without a deploy, and a rollback a variable rather than a release.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, fields
from typing import Literal, get_type_hints

from livekit.agents import inference, llm, stt, tts
from livekit.plugins import anthropic, cartesia, deepgram, openai
from livekit.plugins.deepgram import tts as deepgram_tts

from .cloud_hosting import is_livekit_cloud

logger = logging.getLogger(__name__)

Role = Literal["patient", "tutor"]
Gender = Literal["Female", "Male"]

SETTINGS_ENV_PREFIX = "VOICE_"

# Any model whose id starts with this takes a reasoning effort; see ``_openai_llm``.
REASONING_MODEL_PREFIX = "gpt-5"

# Kept as module constants because other packages and the GPT-Live model
# construction share them; they are the defaults ``SpeechSettings`` starts from.
# The tutor is one persona, Athena, on every provider: a fallback mid-session
# must not change who is speaking. ``coral`` is OpenAI's closest match to
# Deepgram's ``aura-2-athena-en`` that the speech-to-speech model also offers.
TUTOR_VOICE = "coral"
TUTOR_TTS_MODEL = "gpt-4o-mini-tts"
# Patients draw one voice per consultation from these pools; the tutor's Cartesia fallback is fixed.
CARTESIA_FEMALE_VOICES = (
    "2f251ac3-89a9-4a77-a452-704b474ccd01",
    "dc30854e-e398-4579-9dc8-16f6cb2c19b9",
    "fb02b554-7d64-4f90-841e-e57fc88f410c",
    "db408a93-859c-4a0a-b6a2-220c074cc90d",
)
CARTESIA_MALE_VOICES = (
    "ef191366-f52f-447a-a398-ed8c0f2943a1",
    "4bc3cb8c-adb9-4bb8-b5d5-cbbef950b991",
    "d3e3d5d5-07b0-484f-9967-dbc8f15b60d5",
    "bbee10a8-4f08-4c5c-8282-e69299115055",
)
CARTESIA_TUTOR_VOICE_ID = "2f251ac3-89a9-4a77-a452-704b474ccd01"  # Lucy; its own literal so editing the pool never changes the tutor


@dataclass(frozen=True)
class SpeechSettings:
    """The model, voice and style choices for speech, each overridable from the environment."""

    stt_model: str = "nova-3-medical"
    # Both chosen by measurement, not recency: see scripts/model_bench.py. The
    # patient stayed on gpt-4o-mini because gpt-5.4-nano tied on role adherence
    # while costing 84% more and answering more slowly. The tutor moved off
    # gpt-4o because gpt-5.4-mini held the role better for 76% less.
    patient_llm: str = "gpt-4o-mini"
    tutor_llm: str = "gpt-5.4-mini"
    # Live voice has no room for a model that thinks before it speaks. Effort is
    # a setting rather than a constant so a comparison can turn it back on.
    patient_reasoning_effort: str = "none"
    tutor_reasoning_effort: str = "none"
    vision_llm: str = "claude-haiku-4-5"
    fallback_llm: str = "claude-haiku-4-5"
    fallback_temperature: float = 0.8
    tutor_tts_model: str = TUTOR_TTS_MODEL
    tutor_voice: str = TUTOR_VOICE
    tts_style: str = "Speak as a warm, confident and concise clinical education assistant."
    # The patient is a person with a problem, not a second educator. Reading
    # their lines in the tutor's style is what made the two personas blur.
    patient_tts_style: str = "Speak as an ordinary person describing their own symptoms to a doctor."
    deepgram_tutor_voice: str = "aura-2-athena-en"
    # Distinct from the tutor: sharing one voice across two roles is the part of
    # role confusion a listener notices first.
    deepgram_female_voices: str = "aura-2-vesta-en,aura-2-cordelia-en"  # comma-separated pools; each provider indexes its own by the same key
    deepgram_male_voices: str = "aura-2-draco-en,aura-2-pluto-en,aura-2-mars-en"
    # Comma-separated pools; a single id in the variable pins every patient to it.
    cartesia_female_voices: str = ",".join(CARTESIA_FEMALE_VOICES)
    cartesia_male_voices: str = ",".join(CARTESIA_MALE_VOICES)
    cartesia_tutor_voice: str = CARTESIA_TUTOR_VOICE_ID
    # LiveKit Cloud only (Inference "provider/model" ids), EU-served for Frankfurt.
    # The fallback is also the vision model: Gemini reads images.
    cloud_fallback_llm: str = "google/gemini-3.1-flash-lite"
    cloud_tts_model: str = "cartesia/sonic-3.5"

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


def build_stt(settings: SpeechSettings | None = None) -> stt.STT:
    """Build the speech-to-text model."""
    settings = settings or SpeechSettings.from_env()
    if is_livekit_cloud():
        return inference.STT(model=f"deepgram/{settings.stt_model}", language="en")
    return deepgram.STT(model=settings.stt_model, language="en", punctuate=True, interim_results=True)


def _fallback_llm(settings: SpeechSettings) -> llm.LLM:
    """The shared backup model: Inference Gemini on Cloud, Anthropic direct on our own workers."""
    if is_livekit_cloud():
        return inference.LLM(
            model=settings.cloud_fallback_llm, extra_kwargs={"temperature": settings.fallback_temperature}
        )
    return anthropic.LLM(model=settings.fallback_llm, temperature=settings.fallback_temperature)


def _openai_llm(model: str, effort: str) -> llm.LLM:
    """An OpenAI model, with a reasoning effort only where one is meaningful.

    The plugin sets an effort itself, but only for the model ids in its own
    allow-list, which does not cover every current model. A model it does not
    recognise is left to the provider's default, and on a reasoning model that
    default costs seconds before the first word. Sending the effort here covers
    the whole line; older models take no such argument, so they are left alone.
    """
    kwargs = {"reasoning_effort": effort.strip()} if model.startswith(REASONING_MODEL_PREFIX) and effort.strip() else {}
    if is_livekit_cloud():
        return inference.LLM(model=f"openai/{model}", extra_kwargs=kwargs or None)
    return openai.LLM(model=model, **kwargs)


def build_llm(role: Role, settings: SpeechSettings | None = None) -> llm.LLM:
    """Primary model by role, with a shared Anthropic fallback."""
    settings = settings or SpeechSettings.from_env()
    if role == "tutor":
        primary = _openai_llm(settings.tutor_llm, settings.tutor_reasoning_effort)
    else:
        primary = _openai_llm(settings.patient_llm, settings.patient_reasoning_effort)
    return llm.FallbackAdapter([primary, _fallback_llm(settings)])


def build_vision_llm(settings: SpeechSettings | None = None) -> llm.LLM:
    """The image-capable model: tool results carry screenshots as image blocks.

    Wrapped like every other role. A help session is the one place a model blip is
    most visible — the user is mid-navigation, looking at a highlight — and the
    shared fallback reads images too, so there is no reason to run this one bare.
    """
    settings = settings or SpeechSettings.from_env()
    if is_livekit_cloud():
        # Gemini first, then the patient's OpenAI model (it reads images too), so the pair differs.
        return llm.FallbackAdapter([_fallback_llm(settings), _openai_llm(settings.patient_llm, settings.patient_reasoning_effort)])
    return llm.FallbackAdapter([anthropic.LLM(model=settings.vision_llm), _fallback_llm(settings)])


def _pick_voice(pool: str, key: str) -> str:
    """One voice from a comma-separated pool, stable for a key (``hash()`` is salted per process, so use sha256)."""
    voices = [voice.strip() for voice in pool.split(",") if voice.strip()]
    if not voices:
        raise ValueError("a voice pool setting is empty; set at least one voice id")
    return voices[int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(voices)]


def _openai_tts(settings: SpeechSettings, style: str) -> tts.TTS:
    return openai.TTS(model=settings.tutor_tts_model, voice=settings.tutor_voice, instructions=style)


def build_tts(
    role: Role,
    gender: Gender = "Female",
    *,
    voice_key: str = "",
    settings: SpeechSettings | None = None,
) -> tts.TTS:
    """Fallback chain of voices: the tutor uses the shared voice, the patient is gendered.

    Self-hosted: Deepgram, OpenAI, then Cartesia. LiveKit Cloud: the patient is Cartesia
    then Deepgram (Inference), the tutor Deepgram Athena then Cartesia Lucy; OpenAI last.
    ``voice_key`` (the room name, required for a patient) picks the Deepgram and Cartesia voices
    from the gender's pools, so a fallback, reconnect or worker restart in one consultation keeps the same voice.
    """
    settings = settings or SpeechSettings.from_env()
    style = settings.tts_style if role == "tutor" else settings.patient_tts_style
    if role == "tutor":
        deepgram_voice, cartesia_voice = settings.deepgram_tutor_voice, settings.cartesia_tutor_voice
    else:
        if not voice_key:
            raise ValueError("a patient voice needs the consultation's voice_key, or every patient gets one voice")
        female = gender == "Female"
        deepgram_pool = settings.deepgram_female_voices if female else settings.deepgram_male_voices
        cartesia_pool = settings.cartesia_female_voices if female else settings.cartesia_male_voices
        deepgram_voice, cartesia_voice = _pick_voice(deepgram_pool, voice_key), _pick_voice(cartesia_pool, voice_key)
    openai_voice = _openai_tts(settings, style)
    if is_livekit_cloud():
        cartesia_voice_tts = inference.TTS(model=settings.cloud_tts_model, voice=cartesia_voice)
        deepgram_voice_tts = inference.TTS(model="deepgram/aura-2", voice=deepgram_voice)
        order = [deepgram_voice_tts, cartesia_voice_tts] if role == "tutor" else [cartesia_voice_tts, deepgram_voice_tts]
        return tts.FallbackAdapter([*order, openai_voice])
    return tts.FallbackAdapter([deepgram_tts.TTS(model=deepgram_voice), openai_voice, cartesia.TTS(voice=cartesia_voice)])
