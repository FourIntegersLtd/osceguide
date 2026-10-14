"""Speech stacks by role; ported from the legacy TTS/STT tests with the product vocabulary removed."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from livekit.plugins import deepgram

from voice_infra import speech

DG_FEMALE_POOL = ("aura-2-vesta-en", "aura-2-cordelia-en")
DG_MALE_POOL = ("aura-2-draco-en", "aura-2-pluto-en", "aura-2-mars-en")
LUCY = "2f251ac3-89a9-4a77-a452-704b474ccd01"
FEMALE_POOL = (
    LUCY,
    "dc30854e-e398-4579-9dc8-16f6cb2c19b9",  # Victoria
    "fb02b554-7d64-4f90-841e-e57fc88f410c",  # Ailsa
    "db408a93-859c-4a0a-b6a2-220c074cc90d",  # Hana
)
MALE_POOL = (
    "ef191366-f52f-447a-a398-ed8c0f2943a1",  # Archie
    "4bc3cb8c-adb9-4bb8-b5d5-cbbef950b991",  # George
    "d3e3d5d5-07b0-484f-9967-dbc8f15b60d5",  # Ronan
    "bbee10a8-4f08-4c5c-8282-e69299115055",  # Ben
)

# Who each default voice sounds like. A chain that mixes voices is the fallback a
# listener hears as a different person; add a voice here when a default changes.
VOICE_GENDERS = {
    "aura-2-athena-en": "Female",
    **dict.fromkeys(DG_FEMALE_POOL, "Female"),
    **dict.fromkeys(DG_MALE_POOL, "Male"),
    "coral": "Female",
    LUCY: "Female",
    **dict.fromkeys(FEMALE_POOL, "Female"),
    **dict.fromkeys(MALE_POOL, "Male"),
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


@pytest.mark.parametrize(("gender", "model", "voice"), [("Female", DG_FEMALE_POOL, FEMALE_POOL), ("Male", DG_MALE_POOL, MALE_POOL)])
def test_patient_tts_is_gendered(monkeypatch, gender, model, voice) -> None:
    _, deepgram_tts, cartesia_tts, fallback = _patch_tts(monkeypatch)
    speech.build_tts("patient", gender, voice_key="room-1")
    assert fallback.call_args.args[0] == ["deepgram", "openai", "cartesia"]
    assert deepgram_tts.call_args.kwargs["model"] in model
    assert cartesia_tts.call_args.kwargs["voice"] in voice


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
    assert voices == ["aura-2-athena-en", speech.TUTOR_VOICE, LUCY]


def test_every_cloud_tutor_voice_is_the_one_female_persona(cloud, monkeypatch) -> None:
    openai_tts, _, _, fallback = _patch_tts(monkeypatch)
    fallback.side_effect = lambda chain: chain
    chain = speech.build_tts("tutor")
    voices = [t._opts.voice for t in chain[:2]] + [openai_tts.call_args.kwargs["voice"]]
    assert [VOICE_GENDERS.get(v) for v in voices] == ["Female", "Female", "Female"]


@pytest.mark.parametrize("gender", ["Female", "Male"])
def test_patient_voices_match_the_gender_in_the_voice_table(monkeypatch, gender) -> None:
    _, deepgram_tts, cartesia_tts, _ = _patch_tts(monkeypatch)
    speech.build_tts("patient", gender, voice_key="room-1")
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
    speech.build_tts("patient", "Female", voice_key="room-1")
    assert deepgram_tts.call_args.kwargs["model"] != tutor_voice


def test_the_patient_is_not_spoken_in_the_tutor_style(monkeypatch) -> None:
    openai_tts, _, _, _ = _patch_tts(monkeypatch)
    speech.build_tts("tutor")
    tutor_style = openai_tts.call_args.kwargs["instructions"]
    speech.build_tts("patient", "Female", voice_key="room-1")
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
    chain = speech.build_tts("patient", "Male", voice_key="room-1")
    assert [type(t) for t in chain[:2]] == [speech.inference.TTS, speech.inference.TTS]
    assert [t.model for t in chain[:2]] == ["cartesia/sonic-3.5", "deepgram/aura-2"]
    assert [t._opts.voice for t in chain[:2]] == ["bbee10a8-4f08-4c5c-8282-e69299115055", "aura-2-draco-en"]
    assert chain[0]._opts.voice in MALE_POOL
    assert chain[2] == "openai"
    assert openai_tts.call_args.kwargs["model"] == "gpt-4o-mini-tts"


def test_cloud_tutor_chain_starts_with_athena_then_fixed_lucy(cloud, monkeypatch) -> None:
    _, _, _, fallback = _patch_tts(monkeypatch)
    fallback.side_effect = lambda chain: chain
    chain = speech.build_tts("tutor", voice_key="room-1")
    assert [t._opts.voice for t in chain[:2]] == ["aura-2-athena-en", LUCY]
    assert [t.model for t in chain[:2]] == ["deepgram/aura-2", "cartesia/sonic-3.5"]


def test_self_hosted_tutor_chain_starts_with_athena(monkeypatch, not_cloud) -> None:
    _, deepgram_tts, cartesia_tts, fallback = _patch_tts(monkeypatch)
    speech.build_tts("tutor", voice_key="room-1")
    assert fallback.call_args.args[0][0] == "deepgram"
    assert deepgram_tts.call_args.kwargs["model"] == "aura-2-athena-en"
    assert cartesia_tts.call_args.kwargs["voice"] == LUCY


def _cartesia_voice(monkeypatch, gender, key):
    _, _, cartesia_tts, _ = _patch_tts(monkeypatch)
    speech.build_tts("patient", gender, voice_key=key)
    return cartesia_tts.call_args.kwargs["voice"]


@pytest.mark.parametrize("gender", ["Female", "Male"])
def test_same_consultation_keeps_the_same_voice(monkeypatch, gender) -> None:
    assert _cartesia_voice(monkeypatch, gender, "room-abc") == _cartesia_voice(monkeypatch, gender, "room-abc")


def test_consultations_vary_and_pools_never_cross(monkeypatch) -> None:
    keys = [f"attempt-{i}" for i in range(40)]
    female = {_cartesia_voice(monkeypatch, "Female", k) for k in keys}
    male = {_cartesia_voice(monkeypatch, "Male", k) for k in keys}
    assert female == set(FEMALE_POOL)
    assert male == set(MALE_POOL)


def test_a_single_voice_env_overrides_the_pool(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_CARTESIA_MALE_VOICES", "only-one")
    assert _cartesia_voice(monkeypatch, "Male", "room-1") == "only-one"


def test_non_cloud_tts_stays_on_the_plugins(monkeypatch, not_cloud) -> None:
    _, _, _, fallback = _patch_tts(monkeypatch)
    speech.build_tts("tutor")
    assert fallback.call_args.args[0] == ["deepgram", "openai", "cartesia"]


def test_deepgram_patient_voice_is_picked_per_consultation_from_its_pool(monkeypatch, not_cloud) -> None:
    monkeypatch.setenv("VOICE_DEEPGRAM_FEMALE_VOICES", "aura-2-a-en,aura-2-b-en,aura-2-c-en")
    _, deepgram_tts, _, _ = _patch_tts(monkeypatch)
    seen = set()
    for i in range(30):
        speech.build_tts("patient", "Female", voice_key=f"attempt-{i}")
        seen.add(deepgram_tts.call_args.kwargs["model"])
    assert seen == {"aura-2-a-en", "aura-2-b-en", "aura-2-c-en"}
    speech.build_tts("patient", "Male", voice_key="attempt-1")
    assert deepgram_tts.call_args.kwargs["model"] in DG_MALE_POOL


def test_a_patient_needs_a_voice_key_and_an_empty_pool_is_refused(monkeypatch) -> None:
    _patch_tts(monkeypatch)
    with pytest.raises(ValueError, match="voice_key"):
        speech.build_tts("patient", "Female")
    monkeypatch.setenv("VOICE_CARTESIA_FEMALE_VOICES", ",")
    with pytest.raises(ValueError, match="empty"):
        speech.build_tts("patient", "Female", voice_key="room-1")


def test_a_known_room_always_gets_the_same_literal_voice() -> None:
    """sha256 of the key, so the answer is the same in every process (``hash()`` would differ)."""
    assert speech._pick_voice("a,b,c,d", "room-1") == "d"


def test_each_provider_indexes_its_own_pool_by_the_same_key(monkeypatch, not_cloud) -> None:
    """room-1 hashes to 3 mod 4, 1 mod 2 and 0 mod 3, so pool sizes decide each provider's pick."""
    _, deepgram_tts, cartesia_tts, _ = _patch_tts(monkeypatch)
    speech.build_tts("patient", "Female", voice_key="room-1")
    assert (deepgram_tts.call_args.kwargs["model"], cartesia_tts.call_args.kwargs["voice"]) == (
        "aura-2-cordelia-en",
        "db408a93-859c-4a0a-b6a2-220c074cc90d",
    )
    speech.build_tts("patient", "Male", voice_key="room-1")
    assert (deepgram_tts.call_args.kwargs["model"], cartesia_tts.call_args.kwargs["voice"]) == (
        "aura-2-draco-en",
        "bbee10a8-4f08-4c5c-8282-e69299115055",
    )
