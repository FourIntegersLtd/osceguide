"""Speech stacks by role; ported from the legacy TTS/STT tests with the product vocabulary removed."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from livekit.plugins import deepgram

from voice_infra import speech


def _patch_tts(monkeypatch):
    openai_tts = MagicMock(return_value="openai")
    deepgram_tts = MagicMock(return_value="deepgram")
    cartesia_tts = MagicMock(return_value="cartesia")
    fallback = MagicMock(return_value="fallback")
    monkeypatch.setattr(speech.openai, "TTS", openai_tts)
    monkeypatch.setattr(speech.deepgram_tts, "TTS", deepgram_tts)
    monkeypatch.setattr(speech.cartesia, "TTS", cartesia_tts)
    monkeypatch.setattr(speech.tts, "FallbackAdapter", fallback)
    return openai_tts, deepgram_tts, cartesia_tts, fallback


def test_stt_is_deepgram_nova3_medical(monkeypatch) -> None:
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    stt = speech.build_stt()
    assert isinstance(stt, deepgram.STT)
    assert stt.model == "nova-3-medical"


def test_tutor_tts_is_deepgram_then_openai_then_cartesia(monkeypatch) -> None:
    openai_tts, deepgram_tts, _, fallback = _patch_tts(monkeypatch)
    assert speech.build_tts("tutor") == "fallback"
    assert fallback.call_args.args[0] == ["deepgram", "openai", "cartesia"]
    assert deepgram_tts.call_args.kwargs["model"] == "aura-2-athena-en"
    assert openai_tts.call_args.kwargs["voice"] == "marin"
    assert openai_tts.call_args.kwargs["model"] == "gpt-4o-mini-tts"


@pytest.mark.parametrize(("gender", "model", "voice"), [("Female", "aura-2-athena-en", speech.CARTESIA_FEMALE_VOICE_ID), ("Male", "aura-2-hermes-en", speech.CARTESIA_MALE_VOICE_ID)])
def test_patient_tts_is_gendered(monkeypatch, gender, model, voice) -> None:
    _, deepgram_tts, cartesia_tts, fallback = _patch_tts(monkeypatch)
    speech.build_tts("patient", gender)
    assert fallback.call_args.args[0] == ["deepgram", "openai", "cartesia"]
    assert deepgram_tts.call_args.kwargs["model"] == model
    assert cartesia_tts.call_args.kwargs["voice"] == voice


def test_llm_primary_by_role_with_shared_fallback(monkeypatch) -> None:
    openai_llm = MagicMock(side_effect=lambda **kw: f"openai:{kw['model']}")
    anthropic_llm = MagicMock(side_effect=lambda **kw: f"anthropic:{kw['model']}")
    fallback = MagicMock(side_effect=lambda models: models)
    monkeypatch.setattr(speech.openai, "LLM", openai_llm)
    monkeypatch.setattr(speech.anthropic, "LLM", anthropic_llm)
    monkeypatch.setattr(speech.llm, "FallbackAdapter", fallback)
    assert speech.build_llm("patient") == ["openai:gpt-4o-mini", "anthropic:claude-haiku-4-5"]
    assert speech.build_llm("tutor") == ["openai:gpt-4o", "anthropic:claude-haiku-4-5"]
    assert anthropic_llm.call_args.kwargs["temperature"] == 0.8


def test_faq_style_sessions_can_put_openai_first(monkeypatch) -> None:
    _, _, _, fallback = _patch_tts(monkeypatch)
    speech.build_tts("tutor", primary="openai")
    assert fallback.call_args.args[0] == ["openai", "deepgram", "cartesia"]


def test_vision_llm_is_the_image_capable_model_alone(monkeypatch) -> None:
    anthropic_llm = MagicMock(side_effect=lambda **kw: f"anthropic:{kw['model']}")
    monkeypatch.setattr(speech.anthropic, "LLM", anthropic_llm)
    assert speech.build_vision_llm() == "anthropic:claude-haiku-4-5"


def test_models_voices_and_style_are_deployment_settings(monkeypatch) -> None:
    assert speech.SpeechSettings.from_env() == speech.SpeechSettings()
    monkeypatch.setenv("VOICE_TUTOR_LLM", "gpt-5")
    monkeypatch.setenv("VOICE_TTS_STYLE", "Speak as Athena.")
    monkeypatch.setenv("VOICE_FALLBACK_TEMPERATURE", "0.2")
    settings = speech.SpeechSettings.from_env()
    assert settings.tutor_llm == "gpt-5" and settings.tts_style == "Speak as Athena." and settings.fallback_temperature == 0.2
    openai_tts, _, _, _ = _patch_tts(monkeypatch)
    openai_llm = MagicMock(side_effect=lambda **kw: f"openai:{kw['model']}")
    monkeypatch.setattr(speech.openai, "LLM", openai_llm)
    monkeypatch.setattr(speech.anthropic, "LLM", MagicMock())
    monkeypatch.setattr(speech.llm, "FallbackAdapter", lambda models: models)
    assert speech.build_llm("tutor")[0] == "openai:gpt-5"
    speech.build_tts("tutor")
    assert openai_tts.call_args.kwargs["instructions"] == "Speak as Athena."
