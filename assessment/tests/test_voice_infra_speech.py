"""Speech stacks by role; ported from the legacy TTS/STT tests with the product vocabulary removed."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from livekit.plugins import deepgram

from voice_infra import speech

# Who each default voice sounds like. A chain that mixes voices is the fallback a
# listener hears as a different person; add a voice here when a default changes.
VOICE_GENDERS = {
    "aura-2-athena-en": "Female",
    "aura-2-thalia-en": "Female",
    "aura-2-hermes-en": "Male",
    "coral": "Female",
    speech.CARTESIA_FEMALE_VOICE_ID: "Female",
    speech.CARTESIA_MALE_VOICE_ID: "Male",
}


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
    assert openai_tts.call_args.kwargs["voice"] == "coral"
    assert openai_tts.call_args.kwargs["model"] == "gpt-4o-mini-tts"


@pytest.mark.parametrize(("gender", "model", "voice"), [("Female", "aura-2-thalia-en", speech.CARTESIA_FEMALE_VOICE_ID), ("Male", "aura-2-hermes-en", speech.CARTESIA_MALE_VOICE_ID)])
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
    assert speech.build_llm("tutor") == ["openai:gpt-5.4-mini", "anthropic:claude-haiku-4-5"]
    assert anthropic_llm.call_args.kwargs["temperature"] == 0.8


def test_every_tutor_voice_is_the_one_female_persona(monkeypatch) -> None:
    """A provider fallback mid-session must not change who is speaking (C-36)."""
    openai_tts, deepgram_tts, cartesia_tts, _ = _patch_tts(monkeypatch)
    speech.build_tts("tutor")
    voices = [deepgram_tts.call_args.kwargs["model"], openai_tts.call_args.kwargs["voice"], cartesia_tts.call_args.kwargs["voice"]]
    assert [VOICE_GENDERS.get(v) for v in voices] == ["Female", "Female", "Female"]
    assert voices == ["aura-2-athena-en", speech.TUTOR_VOICE, speech.CARTESIA_FEMALE_VOICE_ID]


def test_every_cloud_tutor_voice_is_the_one_female_persona(cloud, monkeypatch) -> None:
    openai_tts, _, _, fallback = _patch_tts(monkeypatch)
    fallback.side_effect = lambda chain: chain
    chain = speech.build_tts("tutor")
    voices = [t._opts.voice for t in chain[:2]] + [openai_tts.call_args.kwargs["voice"]]
    assert [VOICE_GENDERS.get(v) for v in voices] == ["Female", "Female", "Female"]


@pytest.mark.parametrize("gender", ["Female", "Male"])
def test_patient_voices_match_the_gender_in_the_voice_table(monkeypatch, gender) -> None:
    _, deepgram_tts, cartesia_tts, _ = _patch_tts(monkeypatch)
    speech.build_tts("patient", gender)
    voices = [deepgram_tts.call_args.kwargs["model"], cartesia_tts.call_args.kwargs["voice"]]
    assert [VOICE_GENDERS.get(v) for v in voices] == [gender, gender]


def test_vision_llm_has_a_fallback_like_every_other_role(monkeypatch) -> None:
    anthropic_llm = MagicMock(side_effect=lambda **kw: f"anthropic:{kw['model']}")
    monkeypatch.setattr(speech.anthropic, "LLM", anthropic_llm)
    fallback = MagicMock(side_effect=lambda models: {"fallback": models})
    monkeypatch.setattr(speech.llm, "FallbackAdapter", fallback)

    built = speech.build_vision_llm()

    # A model blip is most visible mid-navigation; the shared fallback reads images too.
    assert built == {"fallback": ["anthropic:claude-haiku-4-5", "anthropic:claude-haiku-4-5"]}


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


def test_the_patient_does_not_share_the_tutor_voice(monkeypatch) -> None:
    """Two roles in one voice is the part of role confusion a listener notices first."""
    _, deepgram_tts, _, _ = _patch_tts(monkeypatch)
    speech.build_tts("tutor")
    tutor_voice = deepgram_tts.call_args.kwargs["model"]
    speech.build_tts("patient", "Female")
    assert deepgram_tts.call_args.kwargs["model"] != tutor_voice


def test_the_patient_is_not_spoken_in_the_tutor_style(monkeypatch) -> None:
    openai_tts, _, _, _ = _patch_tts(monkeypatch)
    speech.build_tts("tutor")
    tutor_style = openai_tts.call_args.kwargs["instructions"]
    speech.build_tts("patient", "Female")
    patient_style = openai_tts.call_args.kwargs["instructions"]
    assert patient_style != tutor_style
    assert "clinical education assistant" not in patient_style


def _capture_openai_llm(monkeypatch):
    calls = []
    monkeypatch.setattr(speech.openai, "LLM", lambda **kw: calls.append(kw) or f"openai:{kw['model']}")
    monkeypatch.setattr(speech.anthropic, "LLM", lambda **kw: f"anthropic:{kw['model']}")
    monkeypatch.setattr(speech.llm, "FallbackAdapter", lambda models: models)
    return calls


@pytest.mark.parametrize("model", ["gpt-5.4-nano", "gpt-5.4-mini", "gpt-5.6-luna"])
def test_reasoning_models_are_told_not_to_reason(monkeypatch, model) -> None:
    """A reasoning model left on the provider default thinks for seconds before speaking.

    The plugin only sets an effort for ids on its own allow-list, which does not
    include every current model, so the worker sends it regardless.
    """
    monkeypatch.setenv("VOICE_PATIENT_LLM", model)
    calls = _capture_openai_llm(monkeypatch)
    speech.build_llm("patient")
    assert calls[0] == {"model": model, "reasoning_effort": "none"}


def test_models_that_take_no_reasoning_effort_are_not_sent_one(monkeypatch) -> None:
    calls = _capture_openai_llm(monkeypatch)
    speech.build_llm("patient")
    assert calls[0] == {"model": "gpt-4o-mini"}


def test_the_tutor_default_is_told_not_to_reason() -> None:
    """gpt-5.4-mini is a reasoning model; left on the provider default it thinks before speaking."""
    settings = speech.SpeechSettings()
    assert settings.tutor_llm.startswith(speech.REASONING_MODEL_PREFIX)
    assert settings.tutor_reasoning_effort == "none"


def test_a_blank_effort_leaves_the_provider_default(monkeypatch) -> None:
    """The escape hatch for a caller that wants the provider's own default.

    Not reachable through the environment: ``from_env`` reads a blank variable
    as unset, so this is for a caller building settings directly, such as a
    model comparison sweeping effort levels.
    """
    calls = _capture_openai_llm(monkeypatch)
    speech.build_llm("tutor", speech.SpeechSettings(tutor_llm="gpt-5.4-mini", tutor_reasoning_effort=""))
    assert calls[0] == {"model": "gpt-5.4-mini"}


def test_a_blank_effort_variable_reads_as_unset(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_TUTOR_REASONING_EFFORT", "   ")
    assert speech.SpeechSettings.from_env().tutor_reasoning_effort == "none"


def test_effort_is_a_deployment_setting_like_every_other_field(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_PATIENT_LLM", "gpt-5.4-nano")
    monkeypatch.setenv("VOICE_PATIENT_REASONING_EFFORT", "low")
    calls = _capture_openai_llm(monkeypatch)
    speech.build_llm("patient")
    assert calls[0] == {"model": "gpt-5.4-nano", "reasoning_effort": "low"}


# --- LiveKit Cloud: Inference where it serves the model; self-hosted keeps the plugins ---


@pytest.fixture(params=["", "self-hosted"])
def not_cloud(monkeypatch, request):
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", request.param)


@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setenv("OSCE_LIVEKIT_HOSTING", "cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "k")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "s")
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")


def test_cloud_stt_is_inference_nova3_medical(cloud) -> None:
    stt = speech.build_stt()
    assert isinstance(stt, speech.inference.STT)
    assert stt.model == "deepgram/nova-3-medical"


def test_non_cloud_stt_is_the_deepgram_plugin(monkeypatch, not_cloud) -> None:
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-key")
    assert isinstance(speech.build_stt(), deepgram.STT)


def test_cloud_llm_is_inference_openai_with_gemini_fallback(cloud, monkeypatch) -> None:
    monkeypatch.setattr(speech.llm, "FallbackAdapter", lambda models: models)
    patient = speech.build_llm("patient")
    tutor = speech.build_llm("tutor")
    assert all(isinstance(m, speech.inference.LLM) for m in patient + tutor)
    assert [m.model for m in patient] == ["openai/gpt-4o-mini", "google/gemini-3.1-flash-lite"]
    assert [m.model for m in tutor] == ["openai/gpt-5.4-mini", "google/gemini-3.1-flash-lite"]
    assert tutor[0]._opts.extra_kwargs == {"reasoning_effort": "none"}
    assert patient[0]._opts.extra_kwargs == {}
    assert patient[1]._opts.extra_kwargs == {"temperature": 0.8}


def test_cloud_vision_llm_is_inference_gemini(cloud, monkeypatch) -> None:
    monkeypatch.setattr(speech.llm, "FallbackAdapter", lambda models: models)
    built = speech.build_vision_llm()
    assert [m.model for m in built] == ["google/gemini-3.1-flash-lite", "openai/gpt-4o-mini"]


def test_non_cloud_llm_and_vision_stay_on_the_plugins(monkeypatch, not_cloud) -> None:
    monkeypatch.setattr(speech.openai, "LLM", lambda **kw: f"openai:{kw['model']}")
    monkeypatch.setattr(speech.anthropic, "LLM", lambda **kw: f"anthropic:{kw['model']}")
    monkeypatch.setattr(speech.llm, "FallbackAdapter", lambda models: models)
    assert speech.build_llm("patient") == ["openai:gpt-4o-mini", "anthropic:claude-haiku-4-5"]
    assert speech.build_vision_llm() == ["anthropic:claude-haiku-4-5", "anthropic:claude-haiku-4-5"]


def test_cloud_tts_chain_is_cartesia_then_aura_then_openai(cloud, monkeypatch) -> None:
    openai_tts, _, _, fallback = _patch_tts(monkeypatch)
    fallback.side_effect = lambda chain: chain
    chain = speech.build_tts("patient", "Male")
    assert [type(t) for t in chain[:2]] == [speech.inference.TTS, speech.inference.TTS]
    assert [t.model for t in chain[:2]] == ["cartesia/sonic-3.5", "deepgram/aura-2"]
    assert [t._opts.voice for t in chain[:2]] == [speech.CARTESIA_MALE_VOICE_ID, "aura-2-hermes-en"]
    assert chain[2] == "openai"
    assert openai_tts.call_args.kwargs["model"] == "gpt-4o-mini-tts"


def test_cloud_tutor_tts_uses_the_tutor_voices(cloud, monkeypatch) -> None:
    _, _, _, fallback = _patch_tts(monkeypatch)
    fallback.side_effect = lambda chain: chain
    chain = speech.build_tts("tutor")
    assert [t._opts.voice for t in chain[:2]] == [speech.CARTESIA_FEMALE_VOICE_ID, "aura-2-athena-en"]


def test_non_cloud_tts_stays_on_the_plugins(monkeypatch, not_cloud) -> None:
    _, _, _, fallback = _patch_tts(monkeypatch)
    speech.build_tts("tutor")
    assert fallback.call_args.args[0] == ["deepgram", "openai", "cartesia"]
