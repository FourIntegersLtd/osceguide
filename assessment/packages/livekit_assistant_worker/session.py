"""One assistant job: metadata → bootstrap → candidate → agent → mode-specific handlers."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from livekit.agents import AutoSubscribe, llm, vad
from voice_infra import BackendEndpoints, BackendRegistry
from voice_infra.audio_input import build_room_options
from voice_infra.cloud_slot import register_cloud_slot_lifecycle
from voice_infra.latency import ConversationLatencyTracker
from voice_infra.participants import wait_for_candidate

from osce_assessment.contracts import MessageRole

from .agent_factory import AgentBuild, build_assistant_agent
from .bootstrap import AssistantSession, BootstrapError, fetch_bootstrap
from .gpt_live_policy import register_gpt_live_session_policy
from .metadata import MetadataError, parse_dispatch_metadata
from .prompts import HelpInstructions, OnboardingInstructions, build_help_instructions, build_onboarding_instructions, build_onboarding_scene_update, greeting_for
from .runtime_policy import VoiceRuntime, select_voice_runtime
from .speech import build_assistant_llm, build_assistant_tts
from .tools.help_search import search_help_faqs
from .tools.navigation_mode import build_offer_navigation_modes_tool
from .transcript import GPT_LIVE_LATE_ITEMS_S, TranscriptDelivery, TranscriptRecorder
from .ui_guidance import build_anthropic_computer_tool, is_ui_guidance_enabled

logger = logging.getLogger(__name__)

CANDIDATE_TIMEOUT_S = 30.0
DEFAULT_INSTRUCTIONS = (
    "You are an AI voice agent created by OSCE GUIDE, a company which helps "
    "doctors practise for their clinical simulation exams"
)
TRANSCRIPT_KEEPING_TYPES = ("help",)


def resolve_instructions(session: AssistantSession) -> str:
    """Pure templates render here; data-dependent modes arrive rendered from the backend."""
    if session.worker_type == "help":
        return HelpInstructions().get_help_instructions(screen_ui_guidance=session.extras.screen_ui_guidance)
    if session.worker_type == "onboarding":
        e = session.extras
        return OnboardingInstructions(question=e.onboarding_question or "", patient_line=e.patient_line or "", phase=e.onboarding_phase, user_name=e.user_name).get_onboarding_instructions()
    if session.instructions and session.instructions.strip():
        return session.instructions
    logger.warning("[assistant] %s session arrived without instructions; using the default", session.worker_type)
    return DEFAULT_INSTRUCTIONS


def gpt_live_instructions_for(session: AssistantSession):
    if session.worker_type == "help":
        return build_help_instructions()
    if session.worker_type == "onboarding":
        e = session.extras
        return build_onboarding_instructions(phase=e.onboarding_phase, user_name=e.user_name, question=e.onboarding_question, patient_line=e.patient_line)
    raise ValueError(f"GPT-Live is not supported for {session.worker_type}")


class AssistantVoiceSession:
    def __init__(self, registry: BackendRegistry, *, candidate_timeout: float = CANDIDATE_TIMEOUT_S) -> None:
        self._registry = registry
        self._candidate_timeout = candidate_timeout
        self.session: AssistantSession | None = None
        self.runtime = VoiceRuntime.PIPELINE
        self.recorder: TranscriptRecorder | None = None
        self.delivery: TranscriptDelivery | None = None
        self._agent: Any = None
        self._ctx: Any = None
        self._endpoints: BackendEndpoints | None = None

    # -- lifecycle ---------------------------------------------------------------

    async def entrypoint(self, ctx: Any) -> AssistantSession | None:
        try:
            metadata = parse_dispatch_metadata(getattr(ctx.job, "metadata", None))
        except MetadataError as exc:
            logger.error("[assistant] rejected job: %s", exc)
            return None
        endpoints = self._registry.get(metadata.backend)
        self._ctx, self._endpoints = ctx, endpoints

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

        self.runtime = select_voice_runtime(worker_type=session.worker_type, voice_help_intent=session.extras.voice_help_intent, screen_ui_guidance=session.extras.screen_ui_guidance)
        logger.info("[assistant] type=%s intent=%s runtime=%s", session.worker_type, session.extras.voice_help_intent, self.runtime.value)
        self._ensure_navigation_mode_defaults(ctx)

        instructions = resolve_instructions(session)
        tools = self._tools_for(ctx, session)
        build = await self._start_agent(ctx, session, instructions, tools)
        agent = build.session
        self._agent = agent
        self.runtime = build.runtime

        if session.worker_type in TRANSCRIPT_KEEPING_TYPES:
            self.recorder = TranscriptRecorder(session.session_id)
            self.delivery = TranscriptDelivery(endpoints, self.recorder, worker_type=session.worker_type, candidate_ref=session.candidate_ref)

        if self.runtime is VoiceRuntime.GPT_LIVE and session.worker_type == "help":
            register_gpt_live_session_policy(ctx=ctx, agent=agent, session_id=session.session_id, worker_type=session.worker_type, endpoints=endpoints)

        self._wire_handlers(ctx, agent, session)
        await self._send_initial_greeting(agent, session, build.opening_instruction)
        return session

    # -- setup --------------------------------------------------------------------

    def _tools_for(self, ctx: Any, session: AssistantSession) -> list:
        tools: list = [search_help_faqs]
        if session.worker_type == "help" and session.extras.screen_ui_guidance:
            tools.append(build_offer_navigation_modes_tool(ctx))
            if is_ui_guidance_enabled():
                try:
                    tools.append(build_anthropic_computer_tool(ctx, session.worker_type))
                except Exception as exc:  # noqa: BLE001 — guidance is optional
                    logger.warning("[ui_guidance] computer tool failed to load: %s", exc, exc_info=True)
        if self.runtime is VoiceRuntime.GPT_LIVE and session.worker_type == "onboarding":
            tools = []
        return tools

    def _build(self, ctx: Any, session: AssistantSession, instructions: str, tools: list, runtime: VoiceRuntime) -> AgentBuild:
        proc_userdata = getattr(getattr(ctx, "proc", None), "userdata", None)
        prewarmed = proc_userdata.get("gpt_live_vad") if isinstance(proc_userdata, dict) else None
        return build_assistant_agent(
            runtime=runtime,
            pipeline_instructions=instructions,
            pipeline_tools=tools,
            pipeline_llm=build_assistant_llm(session.worker_type),
            pipeline_tts=build_assistant_tts(session.worker_type, voice_help_intent=session.extras.voice_help_intent),
            max_tool_steps=10 if session.worker_type in ("help", "onboarding") else 5,
            userdata=None,
            gpt_live_instructions=gpt_live_instructions_for(session) if runtime is VoiceRuntime.GPT_LIVE else None,
            gpt_live_vad=prewarmed if isinstance(prewarmed, vad.VAD) else None,
        )

    async def _start_agent(self, ctx: Any, session: AssistantSession, instructions: str, tools: list) -> AgentBuild:
        build = self._build(ctx, session, instructions, tools, self.runtime)
        try:
            if build.runtime is VoiceRuntime.PIPELINE:
                ConversationLatencyTracker(label=f"assistant:{session.worker_type}", room=ctx.room.name).attach(build.session)
            await build.session.start(room=ctx.room, agent=build.definition, room_options=build_room_options())
            return build
        except llm.RealtimeError:
            if build.runtime is not VoiceRuntime.GPT_LIVE:
                raise
            logger.exception("[assistant] GPT-Live failed to start; falling back to pipeline")
            await build.session.aclose()
            build = self._build(ctx, session, instructions, tools, VoiceRuntime.PIPELINE)
            ConversationLatencyTracker(label=f"assistant:{session.worker_type}", room=ctx.room.name).attach(build.session)
            await build.session.start(room=ctx.room, agent=build.definition, room_options=build_room_options())
            return build

    def _ensure_navigation_mode_defaults(self, ctx: Any) -> None:
        ud = getattr(getattr(ctx, "proc", None), "userdata", None)
        if isinstance(ud, dict):
            ud.setdefault("navigation_mode", "guide")

    # -- events -------------------------------------------------------------------

    def _wire_handlers(self, ctx: Any, agent: Any, session: AssistantSession) -> None:
        if self.delivery is not None:
            async def _shutdown_deliver() -> None:
                await self._deliver_transcript_once()

            ctx.add_shutdown_callback(_shutdown_deliver)

        @ctx.room.on("participant_disconnected")
        def _on_participant_disconnected(_participant: Any) -> None:
            logger.info("[assistant] session ended type=%s", session.worker_type)
            if self.delivery is not None:
                asyncio.create_task(self._deliver_transcript_once())

        if session.worker_type == "onboarding":
            @ctx.room.on("data_received")
            def _on_scene_change(data_packet: Any) -> None:
                msg = _json_packet(data_packet)
                if not msg or msg.get("type") != "scene_change":
                    return
                phase = msg.get("phase")
                extras = session.extras
                if phase in ("intro", "demo"):
                    extras.onboarding_phase = phase
                extras.onboarding_question = msg.get("question", "")
                extras.patient_line = msg.get("patientLine", "")
                logger.info("[assistant] scene change phase=%s", extras.onboarding_phase)
                asyncio.create_task(self._handle_scene_change(agent, session))

        if session.worker_type == "help":
            @ctx.room.on("data_received")
            def _on_nav_mode_choice(data_packet: Any) -> None:
                participant = getattr(data_packet, "participant", None)
                if participant is not None and participant.identity == ctx.room.local_participant.identity:
                    return
                msg = _json_packet(data_packet)
                if not msg or msg.get("type") != "nav_mode_choice" or msg.get("mode") not in ("guide", "automate"):
                    return
                self._ensure_navigation_mode_defaults(ctx)
                ud = getattr(getattr(ctx, "proc", None), "userdata", None)
                if isinstance(ud, dict):
                    ud["navigation_mode"] = msg["mode"]
                asyncio.create_task(self._handle_navigation_mode_choice(agent, msg["mode"]))

        @agent.on("user_input_transcribed")
        def _on_user(ev: Any) -> None:
            if getattr(ev, "is_final", False) and self.recorder is not None and str(getattr(ev, "transcript", "")).strip():
                self.recorder.add(MessageRole.USER, ev.transcript.strip())

        @agent.on("conversation_item_added")
        def _on_item(ev: Any) -> None:
            item = getattr(ev, "item", None)
            text = getattr(item, "text_content", None)
            if getattr(item, "role", None) == "assistant" and text and self.recorder is not None:
                self.recorder.add(MessageRole.ASSISTANT, str(text).strip())

    async def _handle_navigation_mode_choice(self, agent: Any, mode: str) -> None:
        if mode == "automate":
            user_input = (
                "[User selected Navigate for me (hands-off). You MUST use perform_click "
                "(never show_pointer) for every click step. Do NOT ask them to tap, click, "
                "or select — they are not touching the UI. After screenshot, perform_click, "
                "then screenshot to verify; continue steps without waiting for 'next'. "
                "Never use perform_click for destructive or submit actions.]"
            )
        else:
            user_input = (
                "[User selected Guide me (highlights). Use only show_pointer; wait for "
                "them to say next between steps. Do not use perform_click.]"
            )
        try:
            await asyncio.wait_for(agent.generate_reply(user_input=user_input), timeout=45.0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("navigation mode reply failed: %s", exc)

    async def _handle_scene_change(self, agent: Any, session: AssistantSession) -> None:
        e = session.extras
        try:
            if self.runtime is VoiceRuntime.GPT_LIVE:
                from livekit.plugins.openai.realtime import GPTLiveSession

                duplex = agent.current_agent.duplex_session
                if not isinstance(duplex, GPTLiveSession):
                    raise RuntimeError("GPT-Live runtime has no active GPTLiveSession")
                context, commentary = build_onboarding_scene_update(question=e.onboarding_question, patient_line=e.patient_line)
                duplex.append_instructions(context)
                duplex.append_commentary(commentary)
                return
            instructions = OnboardingInstructions(question=e.onboarding_question or "", patient_line=e.patient_line or "", phase=e.onboarding_phase, user_name=e.user_name).get_onboarding_instructions()
            await asyncio.wait_for(agent.generate_reply(instructions=instructions, user_input="[New scene started — introduce it now as instructed.]"), timeout=30.0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scene change reply failed: %s", exc)

    async def _send_initial_greeting(self, agent: Any, session: AssistantSession, opening_instruction: str | None) -> None:
        try:
            if self.runtime is VoiceRuntime.GPT_LIVE:
                if not opening_instruction:
                    raise RuntimeError("GPT-Live opening instruction is missing")
                await asyncio.wait_for(agent.generate_reply(instructions=opening_instruction, allow_interruptions=True), timeout=30.0)
            elif session.worker_type == "onboarding":
                await asyncio.wait_for(agent.generate_reply(allow_interruptions=True), timeout=30.0)
            else:
                await asyncio.wait_for(agent.say(session.greeting or greeting_for(session.worker_type), allow_interruptions=True), timeout=10.0)
        except Exception as exc:  # noqa: BLE001 — a lost greeting must not end the session
            logger.error("initial greeting failed: %s", exc)

    async def _deliver_transcript_once(self) -> None:
        if self.delivery is None:
            return
        await self.delivery.deliver_once(settle_s=GPT_LIVE_LATE_ITEMS_S if self.runtime is VoiceRuntime.GPT_LIVE else 0.0)


def _json_packet(data_packet: Any) -> dict[str, Any] | None:
    raw = getattr(data_packet, "data", data_packet)
    if not isinstance(raw, (bytes, bytearray)):
        return None
    try:
        msg = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return msg if isinstance(msg, dict) else None
