"""GPT-Live construction and the shared tool-progress helpers (ported oracles)."""

from __future__ import annotations

from unittest.mock import MagicMock

from voice_infra import gpt_live as gpt_live_module
from voice_infra.gpt_live import GPT_LIVE_MODEL, GPT_LIVE_RESPONSES_MODEL, build_gpt_live_model, build_gpt_live_vad
from voice_infra.speech import TUTOR_VOICE
from voice_infra.tool_log import AGENT_TOOL_PREFIX, log_llm_tool_use_shape
from voice_infra.tool_progress import filler_kwargs, filler_line


def test_build_gpt_live_model_uses_the_pinned_models_and_shared_voice(monkeypatch) -> None:
    factory = MagicMock(return_value="model")
    monkeypatch.setattr(gpt_live_module, "GPTLiveModel", factory)
    assert build_gpt_live_model(backend_instructions="Use the FAQ.") == "model"
    options = factory.call_args.kwargs
    assert options["model"] == GPT_LIVE_MODEL
    assert options["voice"] == TUTOR_VOICE == "coral"
    assert options["responses_options"]["model"] == GPT_LIVE_RESPONSES_MODEL
    assert options["responses_options"]["instructions"] == "Use the FAQ."
    assert options["responses_options"]["parallel_tool_calls"] is False


def test_build_gpt_live_vad_uses_the_interruption_preset(monkeypatch) -> None:
    load = MagicMock(return_value="vad")
    monkeypatch.setattr(gpt_live_module.silero.VAD, "load", load)
    assert build_gpt_live_vad() == "vad"
    assert load.call_args.kwargs["min_silence_duration"] == 0.45


def test_filler_lands_inside_the_wait_rather_than_after_it() -> None:
    kwargs = filler_kwargs()
    # A filler only fires once the session has been idle this long, so a delay
    # longer than the tool it covers never fires at all.
    assert kwargs["delay"] < 2.0 and kwargs["interval"] < 5.0
    # Capped: a tool still running after three fillers is stuck, and the on-screen
    # panel is already saying so.
    assert kwargs["max_steps"] == 3
    assert filler_line(0) != filler_line(1) and filler_line(3) == filler_line(0)


def test_tool_use_log_shape(caplog) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="voice_infra.tools")
    ctx = MagicMock()
    ctx.function_call.call_id = "call-1"
    log_llm_tool_use_shape("computer", {"action": "screenshot"}, run_ctx=ctx)
    assert AGENT_TOOL_PREFIX in caplog.text and '"id": "call-1"' in caplog.text
