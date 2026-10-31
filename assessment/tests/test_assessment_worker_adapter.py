"""The LiveKit adapter: transcript wiring, greeting, end signals, close."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from livekit_assessment_worker import adapter as adapter_module
from livekit_assessment_worker import tools as tools_module
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
        Agent=lambda instructions, tools: {"instructions": instructions, "tools": tools},
        build_tools=lambda ctx, names, context, clock: [f"tool:{n}" for n in names],
        build_stt=lambda: "stt",
        build_llm=lambda role: f"llm:{role}",
        build_tts=lambda role, gender, voice_key="": f"tts:{role}:{gender}",
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
        assert session.started["agent"] == {"instructions": "You are the patient.", "tools": []}
        assert "tool_handling" not in session.kwargs
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


def test_profile_named_tools_are_given_to_the_agent_with_async_tool_handling() -> None:
    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42")
        profile = PROFILE.model_copy(update={"tools": ("a_tool",), "tool_context": {"some": "context"}})
        task = asyncio.create_task(adapter.run(profile, lambda role, text: None))
        await asyncio.sleep(0)
        session = FakeAgentSession.instances[-1]
        await asyncio.sleep(0)
        assert session.started["agent"]["tools"] == ["tool:a_tool"]
        assert session.kwargs["tool_handling"] == adapter_module.ASYNC_TOOL_HANDLING
        ctx.room.emit("disconnected")
        await task

    asyncio.run(scenario())


class _RecordingAgent:
    """The active agent a notice lands on: records every system line pushed into its context."""

    def __init__(self) -> None:
        self.system_lines: list[str] = []
        self.chat_ctx = self

    def copy(self) -> "_RecordingAgent":
        """The notice copies the context, adds a line, and hands the copy back."""
        return self

    def add_message(self, role: str, content: str) -> None:
        """Keep system lines; nothing else reaches the context in this test."""
        if role == "system":
            self.system_lines.append(content)

    async def update_chat_ctx(self, chat_ctx: "_RecordingAgent") -> None:
        """The copy is this object, so there is nothing left to apply."""


def test_a_pacing_plan_starts_the_clock_when_the_session_opens_and_disconnect_stops_it() -> None:
    pacing = {
        "total_seconds": 600,
        "marks": [
            {"at_seconds": 0.01, "note": "[Notice: first mark.]"},
            {"at_seconds": 0.15, "note": "[Notice: a mark after the doctor has left.]"},
        ],
        "phases": [{"until_seconds": 600, "label": "working through the plan"}],
    }

    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42")
        profile = PROFILE.model_copy(update={
            "mode": InteractionMode.TUTOR, "tools": ("check_time",), "tool_context": {"pacing": pacing},
        })
        with patch.object(adapter_module, "build_tools", tools_module.build_tools):
            task = asyncio.create_task(adapter.run(profile, lambda role, text: None))
            await asyncio.sleep(0)
        session = FakeAgentSession.instances[-1]
        agent = _RecordingAgent()
        session.current_agent = agent
        await asyncio.sleep(0.05)
        assert agent.system_lines == ["[Notice: first mark.]"]
        [check_time] = session.started["agent"]["tools"]
        status = await check_time(SimpleNamespace())
        assert status.startswith("About 0 sec gone of 10 min; about 10 min left. You should be in: working through the plan")
        ctx.room.emit("disconnected")
        await task
        await adapter.disconnect()
        await asyncio.sleep(0.2)
        assert agent.system_lines == ["[Notice: first mark.]"], "a mark due after disconnect never lands"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("scenario_gender", "pool"),
    [
        ("female", ("2f251ac3-89a9-4a77-a452-704b474ccd01", "dc30854e-e398-4579-9dc8-16f6cb2c19b9", "fb02b554-7d64-4f90-841e-e57fc88f410c", "db408a93-859c-4a0a-b6a2-220c074cc90d")),
        ("Male", ("ef191366-f52f-447a-a398-ed8c0f2943a1", "4bc3cb8c-adb9-4bb8-b5d5-cbbef950b991", "d3e3d5d5-07b0-484f-9967-dbc8f15b60d5", "bbee10a8-4f08-4c5c-8282-e69299115055")),
        ("F", ("2f251ac3-89a9-4a77-a452-704b474ccd01", "dc30854e-e398-4579-9dc8-16f6cb2c19b9", "fb02b554-7d64-4f90-841e-e57fc88f410c", "db408a93-859c-4a0a-b6a2-220c074cc90d")),
        ("M", ("ef191366-f52f-447a-a398-ed8c0f2943a1", "4bc3cb8c-adb9-4bb8-b5d5-cbbef950b991", "d3e3d5d5-07b0-484f-9967-dbc8f15b60d5", "bbee10a8-4f08-4c5c-8282-e69299115055")),
    ],
)
def test_station_gender_reaches_the_patient_voice_pool(monkeypatch, scenario_gender, pool) -> None:
    """Scenario patient_gender -> adapter -> the real build_tts: the Cartesia voice is from that gender's pool."""
    from voice_infra import speech

    cartesia_tts = MagicMock(return_value="cartesia")
    monkeypatch.setattr(speech.cartesia, "TTS", cartesia_tts)
    monkeypatch.setattr(speech.deepgram_tts, "TTS", MagicMock())
    monkeypatch.setattr(speech.openai, "TTS", MagicMock())
    monkeypatch.setattr(speech.tts, "FallbackAdapter", MagicMock())
    monkeypatch.setattr(adapter_module, "build_tts", speech.build_tts)

    async def scenario():
        ctx = FakeJobContext()
        adapter = LiveKitInteractionAdapter(ctx, candidate_identity="candidate-42", gender=scenario_gender)
        task, _, _ = await _run_until(adapter, ctx, None)
        ctx.room.emit("participant_disconnected", participant("candidate-42"))
        await task

    asyncio.run(scenario())
    assert cartesia_tts.call_args.kwargs["voice"] in pool


def test_a_patient_with_no_gender_is_female_and_logged(caplog) -> None:
    assert adapter_module.voice_gender(PROFILE, None) == "Female"
    assert "missing or unrecognised" in caplog.text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Male, 45", "Male"), ("Mrs", "Female"), ("other", "Female")],
)
def test_voice_gender_accepts_the_wordings_stations_really_carry(raw, expected) -> None:
    assert adapter_module.voice_gender(PROFILE, raw) == expected
