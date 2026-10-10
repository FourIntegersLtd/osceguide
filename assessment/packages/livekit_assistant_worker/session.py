"""One assistant job: metadata → bootstrap → candidate → agent → mode-specific wiring.

Every text the model is given arrives rendered from the backend; this module
only decides runtime, tools and handlers from the mode table.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from livekit.agents import AutoSubscribe, llm, vad
from voice_infra import BackendEndpoints, BackendRegistry
from voice_infra.audio_input import build_room_options
from voice_infra.cloud_slot import register_cloud_slot_lifecycle
from voice_infra.latency import ConversationLatencyTracker
from voice_infra.pacing import InteractionClock, build_check_time_tool
from voice_infra.speech import build_tts
from voice_infra.participants import wait_for_candidate

from . import handlers
from .agent_factory import AgentBuild, build_assistant_agent
from .bootstrap import AssistantSession, BootstrapError, fetch_bootstrap, fetch_scene_instructions
from .gpt_live_policy import register_gpt_live_session_policy
from .metadata import MetadataError, parse_dispatch_metadata
from .runtime_policy import VoiceRuntime, select_voice_runtime
from .session_cap import SessionCap, register_session_cap
from .speech import build_assistant_llm
from .tools.navigation_mode import build_offer_navigation_modes_tool
from .tools.remote import build_remote_tools
from .transcript import GPT_LIVE_LATE_ITEMS_S, TranscriptDelivery, TranscriptRecorder
from .ui_guidance import ComputerToolset, NavigationModeState, build_computer_toolset, is_ui_guidance_enabled
from .ui_guidance.browser import BrowserChannel

logger = logging.getLogger(__name__)

CANDIDATE_TIMEOUT_S = 30.0
GREETING_TIMEOUT_S = 10.0
OPENING_REPLY_TIMEOUT_S = 30.0


class AssistantVoiceSession:
    """Runs one assistant job from dispatch metadata to a spoken opening, and holds the state that job builds up."""

    def __init__(self, registry: BackendRegistry, *, candidate_timeout: float = CANDIDATE_TIMEOUT_S) -> None:
        self._registry = registry
        self._candidate_timeout = candidate_timeout
        self.session: AssistantSession | None = None
        self.runtime = VoiceRuntime.PIPELINE
        self.navigation = NavigationModeState()
        self.guidance: ComputerToolset | None = None
        self.recorder: TranscriptRecorder | None = None
        self.delivery: TranscriptDelivery | None = None
        self._agent: Any = None
        self._endpoints: BackendEndpoints | None = None
        self.clock: InteractionClock | None = None
        self.session_cap: SessionCap | None = None

    # -- lifecycle ---------------------------------------------------------------

    async def entrypoint(self, ctx: Any) -> AssistantSession | None:
        """Run one job: read the metadata, fetch the session, wait for the candidate, start the agent and open the conversation. Returns the session, or None when the job is rejected or cannot start."""
        try:
            metadata = parse_dispatch_metadata(getattr(ctx.job, "metadata", None))
        except MetadataError as exc:
            logger.error("[assistant] rejected job: %s", exc)
            return None
        endpoints = self._registry.get(metadata.backend)
        self._endpoints = endpoints

        await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        ctx.log_context_fields = {"room": ctx.room.name, "session": metadata.session_id}
        register_cloud_slot_lifecycle(ctx, endpoints)

        try:
            session = await asyncio.to_thread(fetch_bootstrap, endpoints, metadata)
        except BootstrapError as exc:
            logger.error("[assistant] bootstrap failed session=%s: %s", metadata.session_id, exc)
            return None
        self.session = session

        try:
            await wait_for_candidate(ctx.room, metadata.candidate_ref or session.candidate_ref, timeout=self._candidate_timeout)
        except asyncio.TimeoutError:
            logger.warning("[assistant] no client joined within %ss session=%s", self._candidate_timeout, metadata.session_id)
            return None

        self.runtime = select_voice_runtime(
            worker_type=session.worker_type, voice_help_intent=session.extras.voice_help_intent,
            screen_ui_guidance=session.extras.screen_ui_guidance, gpt_live_offered=session.gpt_live is not None,
        )
        logger.info("[assistant] type=%s intent=%s runtime=%s", session.worker_type.value, session.extras.voice_help_intent, self.runtime.value)

        build = await self._start_agent(ctx, session, session.instructions, self._tools_for(ctx, session))
        self._agent = build.session
        self.runtime = build.runtime

        if session.mode.keeps_transcript:
            self.recorder = TranscriptRecorder(session.session_id)
            self.delivery = TranscriptDelivery(endpoints, self.recorder, worker_type=session.worker_type.value, candidate_ref=session.candidate_ref)
        if self.runtime is VoiceRuntime.GPT_LIVE:
            register_gpt_live_session_policy(ctx=ctx, agent=build.session, session_id=session.session_id, worker_type=session.worker_type.value, endpoints=endpoints)

        self._wire_handlers(ctx, build.session, session)
        # SEC-008: a hard wall-clock cap, so no runtime runs up unbounded spend.
        # The GPT-Live runtime's own policy ends its sessions far sooner; this is
        # the backstop for the pipeline runtime, which otherwise never ends.
        self.session_cap = register_session_cap(ctx)
        if self.clock is not None:
            self.clock.start(build.session)
            ctx.add_shutdown_callback(self.clock.cancel)
        await self._open(build.session, session, build.opening_instruction)
        return session

    # -- setup --------------------------------------------------------------------

    def _tools_for(self, ctx: Any, session: AssistantSession) -> list:
        """Assemble the tools this mode and session call for: navigation, screen guidance, the clock and the backend's own tools."""
        tools: list = []
        if session.mode.ui_guidance and session.extras.screen_ui_guidance:
            tools.append(build_offer_navigation_modes_tool(ctx))
            if is_ui_guidance_enabled():
                try:
                    self.guidance = build_computer_toolset(ctx, session.worker_type.value, self.navigation)
                    tools.append(self.guidance.as_function_tool())
                except Exception as exc:  # noqa: BLE001 — guidance is optional
                    self.guidance = None
                    logger.warning("[ui_guidance] computer tool failed to load: %s", exc, exc_info=True)
        # Built here because the tool needs it, started later: time zero is when the
        # interaction opens, not when the tool list is assembled. A backend that sends
        # no plan gets no clock and no tool, which is the old behaviour exactly.
        if session.mode.paced and session.extras.pacing is not None:
            self.clock = InteractionClock(session.extras.pacing)
            tools.append(build_check_time_tool(self.clock))
        # The backend's own tools: schema from the bootstrap, every call forwarded
        # back to it. A backend that names none gets none, whatever the mode.
        if session.mode.remote_tools and session.tools:
            assert self._endpoints is not None
            tools.extend(build_remote_tools(self._endpoints, session.session_id, session.tools, publish=BrowserChannel(ctx.room).publish))
        return tools

    def _build(self, ctx: Any, session: AssistantSession, instructions: str, tools: list, runtime: VoiceRuntime) -> AgentBuild:
        """Build the agent for the chosen runtime, reusing a voice activity detector warmed up at process start when there is one."""
        proc_userdata = getattr(getattr(ctx, "proc", None), "userdata", None)
        prewarmed = proc_userdata.get("gpt_live_vad") if isinstance(proc_userdata, dict) else None
        return build_assistant_agent(
            runtime=runtime,
            pipeline_instructions=instructions,
            pipeline_tools=tools,
            pipeline_llm=build_assistant_llm(session.mode),
            pipeline_tts=build_tts("tutor"),  # one voice chain for every session type
            max_tool_steps=session.mode.max_tool_steps,
            userdata=None,
            gpt_live_instructions=session.gpt_live if runtime is VoiceRuntime.GPT_LIVE else None,
            gpt_live_vad=prewarmed if isinstance(prewarmed, vad.VAD) else None,
            guidance_toolset=self.guidance if runtime is VoiceRuntime.PIPELINE else None,
        )

    async def _start_agent(self, ctx: Any, session: AssistantSession, instructions: str, tools: list) -> AgentBuild:
        """Start the agent, falling back to the pipeline runtime if the speech-to-speech one fails to start."""
        build = self._build(ctx, session, instructions, tools, self.runtime)
        try:
            return await self._start(ctx, session, build)
        except llm.RealtimeError:
            if build.runtime is not VoiceRuntime.GPT_LIVE:
                raise
            logger.exception("[assistant] GPT-Live failed to start; falling back to pipeline")
            await build.session.aclose()
            return await self._start(ctx, session, self._build(ctx, session, instructions, tools, VoiceRuntime.PIPELINE))

    async def _start(self, ctx: Any, session: AssistantSession, build: AgentBuild) -> AgentBuild:
        """Attach latency logging when needed and start the agent session in the room."""
        if build.runtime is VoiceRuntime.PIPELINE:
            ConversationLatencyTracker(label=f"assistant:{session.worker_type.value}", room=ctx.room.name).attach(build.session)
        await build.session.start(room=ctx.room, agent=build.definition, room_options=build_room_options())
        return build

    # -- events -------------------------------------------------------------------

    def _wire_handlers(self, ctx: Any, agent: Any, session: AssistantSession) -> None:
        """Connect the event handlers this mode needs: transcript capture, scene changes, navigation choices and guidance progress."""
        if self.recorder is not None:
            handlers.wire_transcript_capture(agent, self.recorder)
            handlers.wire_delivery_on_end(ctx, self._deliver_transcript_once)
        if session.mode.scene_updates:
            handlers.wire_scene_changes(ctx, agent, self._render_scene)
        if session.mode.ui_guidance:
            handlers.wire_navigation_mode_choice(ctx, agent, self.navigation)
        if self.guidance is not None:
            handlers.wire_guidance_progress(agent, self.guidance.progress)

    async def _open(self, agent: Any, session: AssistantSession, opening_instruction: str | None) -> None:
        """Speak the backend's greeting, or let the model open when the mode or the backend leaves it to the model."""
        try:
            if self.runtime is VoiceRuntime.GPT_LIVE:
                if not opening_instruction:
                    raise RuntimeError("GPT-Live opening instruction is missing")
                await asyncio.wait_for(agent.generate_reply(instructions=opening_instruction, allow_interruptions=True), timeout=OPENING_REPLY_TIMEOUT_S)
            elif session.mode.opens_with_generated_reply or not (session.greeting or "").strip():
                await asyncio.wait_for(agent.generate_reply(allow_interruptions=True), timeout=OPENING_REPLY_TIMEOUT_S)
            else:
                await asyncio.wait_for(agent.say(session.greeting, allow_interruptions=True), timeout=GREETING_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001 — a lost greeting must not end the session
            logger.error("initial greeting failed: %s", exc)

    async def _render_scene(self, scene: dict[str, Any]) -> str:
        """Ask the backend for the instructions that fit a newly announced scene."""
        assert self.session is not None and self._endpoints is not None
        return await asyncio.to_thread(fetch_scene_instructions, self._endpoints, self.session.session_id, scene)

    async def _deliver_transcript_once(self) -> None:
        """Send the transcript to the backend, once, however many teardown paths call this."""
        if self.delivery is None:
            return
        await self.delivery.deliver_once(settle_s=GPT_LIVE_LATE_ITEMS_S if self.runtime is VoiceRuntime.GPT_LIVE else 0.0)
