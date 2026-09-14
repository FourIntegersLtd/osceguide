"""Construct the AgentSession/Agent pair for the selected voice runtime."""

from __future__ import annotations

from dataclasses import dataclass

from livekit.agents import Agent, AgentSession, llm, tts, vad
from voice_infra.gpt_live import build_gpt_live_model, build_gpt_live_vad
from voice_infra.speech import build_stt
from voice_infra.turn_handling import MIN_CONSECUTIVE_SPEECH_DELAY, build_turn_handling_options

from .prompts.gpt_live import GPTLiveInstructions
from .runtime_policy import VoiceRuntime

ASYNC_TOOL_HANDLING = {
    "async_options": {
        "update_template": (
            "Background tool `{function_name}` reports: {message}. "
            "Acknowledge briefly in plain speech. Do not use markdown."
        ),
    },
}


@dataclass(frozen=True)
class AgentBuild:
    session: AgentSession
    definition: Agent
    runtime: VoiceRuntime
    opening_instruction: str | None = None


def build_assistant_agent(
    *,
    runtime: VoiceRuntime,
    pipeline_instructions: str,
    pipeline_tools: list[llm.Tool | llm.Toolset],
    pipeline_llm: llm.LLM,
    pipeline_tts: tts.TTS,
    max_tool_steps: int,
    userdata: object | None,
    gpt_live_instructions: GPTLiveInstructions | None,
    gpt_live_vad: vad.VAD | None = None,
) -> AgentBuild:
    if runtime is VoiceRuntime.GPT_LIVE:
        if gpt_live_instructions is None:
            raise ValueError("GPT-Live instructions are required for GPT-Live sessions")
        session = AgentSession(
            llm=build_gpt_live_model(backend_instructions=gpt_live_instructions.backend),
            vad=gpt_live_vad or build_gpt_live_vad(),
            max_tool_steps=max_tool_steps,
            session_close_transcript_timeout=5.0,
            userdata=userdata,
            tool_handling=ASYNC_TOOL_HANDLING,
        )
        return AgentBuild(
            session=session,
            definition=Agent(instructions=gpt_live_instructions.voice, tools=pipeline_tools),
            runtime=runtime,
            opening_instruction=gpt_live_instructions.opening,
        )

    session = AgentSession(
        stt=build_stt(),
        llm=pipeline_llm,
        tts=pipeline_tts,
        turn_handling=build_turn_handling_options(),
        min_consecutive_speech_delay=MIN_CONSECUTIVE_SPEECH_DELAY,
        max_tool_steps=max_tool_steps,
        userdata=userdata,
        tool_handling=ASYNC_TOOL_HANDLING,
    )
    return AgentBuild(session=session, definition=Agent(instructions=pipeline_instructions, tools=pipeline_tools), runtime=runtime)
