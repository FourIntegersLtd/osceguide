"""The LiveKit adapter: transcript wiring, greeting, end signals, close."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from livekit_assessment_worker import adapter as adapter_module
from livekit_assessment_worker.adapter import LiveKitInteractionAdapter, role_for
from osce_assessment.contracts import AIInteractionProfile, InteractionMode, MessageRole

from _worker_fakes import FakeAgentSession, FakeJobContext, conversation_item, participant, user_transcribed

PROFILE = AIInteractionProfile(mode=InteractionMode.PATIENT, instructions="You are the patient.")


@pytest.fixture(autouse=True)
def _fake_livekit():
    FakeAgentSession.instances.clear()
    with patch.multiple(
        adapter_module,
        AgentSession=FakeAgentSession,
        Agent=lambda instructions: {"instructions": instructions},
        build_stt=lambda: "stt",
        build_llm=lambda role: f"llm:{role}",
        build_tts=lambda role, gender: f"tts:{role}:{gender}",
        build_turn_handling_options=lambda: "turn",
        build_room_options=lambda **kw: kw,
        ConversationLatencyTracker=lambda **kw: MagicMock(),
    ):
        yield


def test_role_follows_the_profile_mode() -> None:
    assert role_for(PROFILE) == "patient"
    assert role_for(PROFILE.model_copy(update={"mode": InteractionMode.TUTOR})) == "tutor"


async def _run_until(adapter, ctx, end):
    captured = []

    async def on_message(role, text):
        captured.append((role, text))

    task = asyncio.create_task(adapter.run(PROFILE, on_message))
    await asyncio.sleep(0)
    session = FakeAgentSession.instances[-1]
    await asyncio.sleep(0)
    return task, session, captured


def test_speech_stack_is_built_for_the_role_and_audio_pinned_to_the_candidate() -> None:
    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42", gender="male")
        await adapter.send_greeting("Hello doctor.")
        task, session, _ = await _run_until(adapter, ctx, None)
        assert session.kwargs["stt"] == "stt"
        assert session.kwargs["llm"] == "llm:patient"
        assert session.kwargs["tts"] == "tts:patient:Male"
        assert session.started["agent"] == {"instructions": "You are the patient."}
        assert session.started["room_options"] == {"participant_identity": "candidate-42"}
        assert session.said == [("Hello doctor.", {"allow_interruptions": True})]
        ctx.room.emit("participant_disconnected", participant("candidate-42"))
        await task

    asyncio.run(scenario())


def test_final_user_turns_and_assistant_items_reach_the_callback() -> None:
    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42")
        task, session, captured = await _run_until(adapter, ctx, None)
        session.emit("user_input_transcribed", user_transcribed("partial", is_final=False))
        session.emit("user_input_transcribed", user_transcribed("  What brings you in?  "))
        session.emit("conversation_item_added", conversation_item("Chest pain.", role="assistant"))
        session.emit("conversation_item_added", conversation_item("ignored", role="user"))
        session.emit("conversation_item_added", conversation_item("   ", role="assistant"))
        await asyncio.sleep(0)
        ctx.room.emit("disconnected")
        await task
        assert captured == [(MessageRole.USER, "What brings you in?"), (MessageRole.ASSISTANT, "Chest pain.")]

    asyncio.run(scenario())


def test_another_participant_leaving_does_not_end_the_interaction() -> None:
    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42")
        task, _, _ = await _run_until(adapter, ctx, None)
        ctx.room.emit("participant_disconnected", participant("observer"))
        await asyncio.sleep(0)
        assert not task.done()
        await ctx.shutdown_callbacks[0]()
        await task

    asyncio.run(scenario())


def test_disconnect_closes_the_session_once() -> None:
    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42")
        task, session, _ = await _run_until(adapter, ctx, None)
        ctx.room.emit("disconnected")
        await task
        await adapter.disconnect()
        await adapter.disconnect()
        assert session.closed is True

    asyncio.run(scenario())
