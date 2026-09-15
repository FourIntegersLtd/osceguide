"""Runtime selection, agent construction, speech choice (ported oracles)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from livekit_assistant_worker import agent_factory
from livekit_assistant_worker.agent_factory import build_assistant_agent
from livekit_assistant_worker.bootstrap import GPTLiveInstructions
from livekit_assistant_worker.runtime_policy import VoiceRuntime, select_voice_runtime


def test_gpt_live_only_for_faq_help_with_credentials(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert select_voice_runtime(worker_type="help", voice_help_intent="faq", screen_ui_guidance=False) is VoiceRuntime.GPT_LIVE
    assert select_voice_runtime(worker_type="onboarding", voice_help_intent=None, screen_ui_guidance=False) is VoiceRuntime.PIPELINE
    for intent, screen in (("guide", True), ("guide", False), ("faq", True)):
        assert select_voice_runtime(worker_type="help", voice_help_intent=intent, screen_ui_guidance=screen) is VoiceRuntime.PIPELINE
    assert select_voice_runtime(worker_type="help", voice_help_intent="faq", screen_ui_guidance=False, gpt_live_offered=False) is VoiceRuntime.PIPELINE
    monkeypatch.delenv("OPENAI_API_KEY")
    assert select_voice_runtime(worker_type="help", voice_help_intent="faq", screen_ui_guidance=False) is VoiceRuntime.PIPELINE


def test_gpt_live_build_has_no_pipeline_models(monkeypatch) -> None:
    agent_session, agent = MagicMock(return_value="session"), MagicMock(return_value="definition")
    monkeypatch.setattr(agent_factory, "AgentSession", agent_session)
    monkeypatch.setattr(agent_factory, "Agent", agent)
    monkeypatch.setattr(agent_factory, "build_gpt_live_model", MagicMock(return_value="gpt-live"))
    monkeypatch.setattr(agent_factory, "build_gpt_live_vad", MagicMock(return_value="vad"))
    build = build_assistant_agent(
        runtime=VoiceRuntime.GPT_LIVE, pipeline_instructions="pipeline", pipeline_tools=[], pipeline_llm=MagicMock(), pipeline_tts=MagicMock(),
        max_tool_steps=10, userdata=None, gpt_live_instructions=GPTLiveInstructions(voice="voice", backend="backend", opening="opening"),
    )
    assert build.runtime is VoiceRuntime.GPT_LIVE and build.opening_instruction == "opening"
    kwargs = agent_session.call_args.kwargs
    assert kwargs["llm"] == "gpt-live" and kwargs["vad"] == "vad" and "stt" not in kwargs and "tts" not in kwargs
    agent.assert_called_once_with(instructions="voice", tools=[])


def test_pipeline_build_preserves_the_stack(monkeypatch) -> None:
    agent_session, agent = MagicMock(return_value="session"), MagicMock(return_value="definition")
    monkeypatch.setattr(agent_factory, "AgentSession", agent_session)
    monkeypatch.setattr(agent_factory, "Agent", agent)
    monkeypatch.setattr(agent_factory, "build_stt", MagicMock(return_value="stt"))
    monkeypatch.setattr(agent_factory, "build_turn_handling_options", MagicMock(return_value="turns"))
    pipeline_llm, pipeline_tts = MagicMock(), MagicMock()
    build = build_assistant_agent(
        runtime=VoiceRuntime.PIPELINE, pipeline_instructions="pipeline instructions", pipeline_tools=[], pipeline_llm=pipeline_llm, pipeline_tts=pipeline_tts,
        max_tool_steps=5, userdata=None, gpt_live_instructions=None,
    )
    assert build.runtime is VoiceRuntime.PIPELINE
    kwargs = agent_session.call_args.kwargs
    assert (kwargs["stt"], kwargs["llm"], kwargs["tts"], kwargs["turn_handling"]) == ("stt", pipeline_llm, pipeline_tts, "turns")
    agent.assert_called_once_with(instructions="pipeline instructions", tools=[])


def test_gpt_live_build_requires_instructions() -> None:
    with pytest.raises(ValueError, match="GPT-Live instructions"):
        build_assistant_agent(runtime=VoiceRuntime.GPT_LIVE, pipeline_instructions="", pipeline_tools=[], pipeline_llm=MagicMock(), pipeline_tts=MagicMock(), max_tool_steps=1, userdata=None, gpt_live_instructions=None)


def test_speech_choices_come_from_the_mode_table(monkeypatch) -> None:
    from livekit_assistant_worker import speech
    from livekit_assistant_worker.modes import WorkerType, mode_profile

    monkeypatch.setattr(speech, "build_vision_llm", lambda: "vision")
    monkeypatch.setattr(speech, "build_llm", lambda role: f"llm:{role}")
    monkeypatch.setattr(speech, "build_tts", lambda role, **kw: (role, kw["primary"]))
    assert speech.build_assistant_llm(mode_profile(WorkerType.HELP)) == "vision"
    assert speech.build_assistant_llm(mode_profile(WorkerType.ONBOARDING)) == "vision"
    assert speech.build_assistant_llm(mode_profile(WorkerType.CONSULTING_DOCTOR)) == "llm:tutor"
    assert speech.build_assistant_llm(mode_profile(WorkerType.DASHBOARD)) == "llm:patient"
    assert speech.build_assistant_tts(mode_profile(WorkerType.HELP), voice_help_intent="faq") == ("tutor", "openai")
    assert speech.build_assistant_tts(mode_profile(WorkerType.HELP), voice_help_intent="guide") == ("tutor", "deepgram")
    assert speech.build_assistant_tts(mode_profile(WorkerType.DASHBOARD)) == ("tutor", "deepgram")
