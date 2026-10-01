"""Construct the AgentSession/Agent pair for the selected voice runtime."""

from __future__ import annotations

from dataclasses import dataclass

from livekit.agents import Agent, AgentSession, llm, tts, vad
from voice_infra.gpt_live import build_gpt_live_model, build_gpt_live_vad
from voice_infra.speech import build_stt
from voice_infra.tool_handling import ASYNC_TOOL_HANDLING
from voice_infra.turn_handling import MIN_CONSECUTIVE_SPEECH_DELAY, build_turn_handling_options

from .bootstrap import GPTLiveInstructions
from .runtime_policy import VoiceRuntime
from .ui_guidance import ComputerToolset, GuidanceAgent

__all__ = ["ASYNC_TOOL_HANDLING", "AgentBuild", "build_assistant_agent"]


@dataclass(frozen=True)
class AgentBuild:
    """An assistant agent ready to start: the session, the agent definition, the runtime in use and any opening instruction."""

    session: AgentSession
    definition: Agent
    runtime: VoiceRuntime
    opening_instruction: str | None = None


def _definition(
    instructions: str,
    tools: list[llm.Tool | llm.Toolset],
    guidance_toolset: ComputerToolset | None,
) -> Agent:
    """A guidance session needs the agent that strips inline pointer tags."""
    if guidance_toolset is None:
        return Agent(instructions=instructions, tools=tools)
    return GuidanceAgent(toolset=guidance_toolset, instructions=instructions, tools=tools)


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
    guidance_toolset: ComputerToolset | None = None,
) -> AgentBuild:
    """Build the agent session and definition for the chosen runtime, either speech-to-speech or the speech-to-text pipeline."""
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
    return AgentBuild(
        session=session,
        definition=_definition(pipeline_instructions, pipeline_tools, guidance_toolset),
        runtime=runtime,
    )
