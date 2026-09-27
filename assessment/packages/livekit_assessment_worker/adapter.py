"""The engine's InteractionAdapter, implemented on a LiveKit AgentSession.

Everything LiveKit-specific lives here: building the speech stack for the
profile's role, wiring transcript events to the runtime's callback, pinning
audio to the candidate, and ending the interaction when the candidate leaves
or the job shuts down.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from livekit.agents import Agent, AgentSession
from osce_assessment.contracts import AIInteractionProfile, InteractionMode, MessageCallback, MessageRole
from osce_assessment.runtime._awaitable import maybe_await
from voice_infra.audio_input import build_room_options
from voice_infra.latency import ConversationLatencyTracker
from voice_infra.pacing import InteractionClock
from voice_infra.speech import build_llm, build_stt, build_tts
from voice_infra.tool_handling import ASYNC_TOOL_HANDLING
from voice_infra.turn_handling import MIN_CONSECUTIVE_SPEECH_DELAY, build_turn_handling_options

from .notices import wire_time_warnings
from .tools import build_tools, session_clock

logger = logging.getLogger(__name__)

GREETING_TIMEOUT_S = 10.0


def role_for(profile: AIInteractionProfile) -> str:
    return "tutor" if profile.mode is InteractionMode.TUTOR else "patient"


def voice_gender(profile: AIInteractionProfile, default: str | None) -> str:
    """The profile's ``voice`` names the gendered voice; the scenario's patient gender is the fallback."""
    chosen = (profile.voice or default or "").strip().lower()
    return "Male" if chosen == "male" else "Female"


class LiveKitInteractionAdapter:
    def __init__(self, ctx: Any, *, candidate_identity: str, gender: str | None = None, label: str = "assessment") -> None:
        self._ctx = ctx
        self._candidate_identity = candidate_identity
        self._default_gender = gender
        self._label = label
        self._session: AgentSession | None = None
        self._greeting: str | None = None
        self._ended: asyncio.Future | None = None
        self._clock: InteractionClock | None = None

    async def connect(self) -> None:
        # The job connected to the room before the candidate was awaited; nothing to do.
        return None

    async def send_greeting(self, text: str) -> None:
        # Spoken right after the session starts inside ``run``.
        self._greeting = text

    async def run(self, profile: AIInteractionProfile, on_message: MessageCallback) -> None:
        loop = asyncio.get_running_loop()
        self._ended = loop.create_future()
        role = role_for(profile)
        self._clock = session_clock(profile.tool_context)
        tools = build_tools(self._ctx, profile.tools, profile.tool_context, self._clock)
        session_kwargs: dict[str, Any] = dict(
            stt=build_stt(),
            llm=build_llm(role),
            tts=build_tts(role, voice_gender(profile, self._default_gender)),
            turn_handling=build_turn_handling_options(),
            min_consecutive_speech_delay=MIN_CONSECUTIVE_SPEECH_DELAY,
            max_tool_steps=profile.max_tool_steps,
        )
        if tools:
            session_kwargs["tool_handling"] = ASYNC_TOOL_HANDLING
        session = AgentSession(**session_kwargs)
        self._session = session
        ConversationLatencyTracker(label=self._label, room=self._ctx.room.name).attach(session)
        self._wire_transcript(session, on_message)
        self._wire_end_signals()
        wire_time_warnings(self._ctx, session, self._candidate_identity)

        await session.start(
            room=self._ctx.room,
            agent=Agent(instructions=profile.instructions, tools=tools),
            room_options=build_room_options(participant_identity=self._candidate_identity),
        )
        # Time zero is the session opening, before the greeting: the greeting is part of the time.
        if self._clock is not None:
            self._clock.start(session)
        if self._greeting:
            try:
                await asyncio.wait_for(session.say(self._greeting, allow_interruptions=True), timeout=GREETING_TIMEOUT_S)
            except Exception as exc:  # noqa: BLE001 — a lost greeting must not end the session
                logger.warning("greeting failed: %s", exc)
        await self._ended

    async def disconnect(self) -> None:
        clock, self._clock = self._clock, None
        if clock is not None:
            await clock.cancel()
        session, self._session = self._session, None
        if session is None:
            return
        try:
            await session.aclose()
        except Exception as exc:  # noqa: BLE001 — best effort
            logger.warning("session close failed: %s", exc)

    # -- wiring ----------------------------------------------------------------

    def _wire_transcript(self, session: AgentSession, on_message: MessageCallback) -> None:
        @session.on("user_input_transcribed")
        def _on_user(ev: Any) -> None:
            if getattr(ev, "is_final", False) and str(getattr(ev, "transcript", "")).strip():
                asyncio.create_task(maybe_await(on_message(MessageRole.USER, ev.transcript.strip())))

        @session.on("conversation_item_added")
        def _on_item(ev: Any) -> None:
            item = getattr(ev, "item", None)
            if getattr(item, "role", None) != "assistant":
                return
            text = getattr(item, "text_content", None)
            if text and str(text).strip():
                asyncio.create_task(maybe_await(on_message(MessageRole.ASSISTANT, str(text).strip())))

    def _wire_end_signals(self) -> None:
        def end(reason: str) -> None:
            if self._ended is not None and not self._ended.done():
                logger.info("interaction ended: %s", reason)
                self._ended.set_result(reason)

        @self._ctx.room.on("participant_disconnected")
        def _on_participant_disconnected(participant: Any) -> None:
            if getattr(participant, "identity", None) == self._candidate_identity:
                end("candidate disconnected")

        @self._ctx.room.on("disconnected")
        def _on_room_disconnected(*_: Any) -> None:
            end("room disconnected")

        async def _on_shutdown() -> None:
            end("job shutdown")

        self._ctx.add_shutdown_callback(_on_shutdown)
