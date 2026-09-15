"""The candidate's clock warns the room; the persona winds down without speaking over them."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from livekit_assessment_worker import adapter as adapter_module
from livekit_assessment_worker.adapter import LiveKitInteractionAdapter
from livekit_assessment_worker.notices import apply_notice, seconds_left_from, time_remaining_notice, wire_time_warnings
from osce_assessment.contracts import AIInteractionProfile, InteractionMode

from _worker_fakes import FakeAgentSession, FakeJobContext, participant

PROFILE = AIInteractionProfile(mode=InteractionMode.PATIENT, instructions="You are the patient.")


class FakeChatCtx:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def copy(self) -> "FakeChatCtx":
        clone = FakeChatCtx()
        clone.messages = list(self.messages)
        return clone

    def add_message(self, role: str, content: str) -> None:
        self.messages.append((role, content))


def fake_session():
    agent = SimpleNamespace(chat_ctx=FakeChatCtx(), update_chat_ctx=AsyncMock())
    return SimpleNamespace(current_agent=agent, generate_reply=MagicMock(), say=AsyncMock()), agent


def packet(payload: dict, identity: str = "candidate-42") -> SimpleNamespace:
    return SimpleNamespace(data=json.dumps(payload).encode(), participant=participant(identity))


async def settle() -> None:
    for _ in range(3):
        await asyncio.sleep(0)


def test_notice_is_appended_as_system_context_and_forces_no_reply() -> None:
    session, agent = fake_session()
    asyncio.run(apply_notice(session, time_remaining_notice(30)))
    agent.update_chat_ctx.assert_awaited_once()
    (ctx,) = agent.update_chat_ctx.await_args.args
    assert ctx.messages == [("system", time_remaining_notice(30))]
    assert "30 seconds" in ctx.messages[0][1]
    session.generate_reply.assert_not_called()
    session.say.assert_not_awaited()


def test_apply_notice_never_raises() -> None:
    session, agent = fake_session()
    agent.update_chat_ctx.side_effect = RuntimeError("boom")
    asyncio.run(apply_notice(session, "x"))
    asyncio.run(apply_notice(SimpleNamespace(current_agent=None), "x"))


def test_seconds_left_parsing_rejects_junk() -> None:
    assert seconds_left_from({"secondsLeft": 30}) == 30
    assert seconds_left_from({"secondsLeft": "15"}) == 15
    assert seconds_left_from({"secondsLeft": 0}) is None
    assert seconds_left_from({"secondsLeft": "soon"}) is None
    assert seconds_left_from({}) is None


def test_only_the_candidates_time_warning_is_honoured() -> None:
    async def scenario():
        ctx = FakeJobContext()
        session, agent = fake_session()
        wire_time_warnings(ctx, session, "candidate-42")

        ctx.room.emit("data_received", packet({"type": "time_warning", "secondsLeft": 30}, identity="supervisor-7"))
        ctx.room.emit("data_received", packet({"type": "scene_change"}))
        ctx.room.emit("data_received", SimpleNamespace(data="not bytes", participant=participant("candidate-42")))
        await settle()
        agent.update_chat_ctx.assert_not_awaited()

        ctx.room.emit("data_received", packet({"type": "time_warning", "secondsLeft": 30}))
        await settle()
        agent.update_chat_ctx.assert_awaited_once()

    asyncio.run(scenario())


def test_adapter_wires_time_warnings_for_the_running_session() -> None:
    FakeAgentSession.instances.clear()
    with patch.multiple(
        adapter_module,
        AgentSession=FakeAgentSession,
        Agent=lambda instructions, tools: {"instructions": instructions, "tools": tools},
        build_tools=lambda ctx, names, context: [],
        build_stt=lambda: "stt",
        build_llm=lambda role: "llm",
        build_tts=lambda role, gender: "tts",
        build_turn_handling_options=lambda: "turn",
        build_room_options=lambda **kw: kw,
        ConversationLatencyTracker=lambda **kw: MagicMock(),
    ):
        async def scenario():
            ctx = FakeJobContext()
            adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42")
            task = asyncio.create_task(adapter.run(PROFILE, AsyncMock()))
            await settle()
            session = FakeAgentSession.instances[-1]
            session.current_agent = SimpleNamespace(chat_ctx=FakeChatCtx(), update_chat_ctx=AsyncMock())

            ctx.room.emit("data_received", packet({"type": "time_warning", "secondsLeft": 30}))
            await settle()
            session.current_agent.update_chat_ctx.assert_awaited_once()

            ctx.room.emit("participant_disconnected", participant("candidate-42"))
            await task

        asyncio.run(scenario())
