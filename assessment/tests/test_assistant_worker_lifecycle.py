"""One assistant job against fakes, per session type."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from livekit_assistant_worker import session as session_module
from livekit_assistant_worker.agent_factory import AgentBuild
from livekit_assistant_worker.bootstrap import AssistantSession
from livekit_assistant_worker.runtime_policy import VoiceRuntime
from livekit_assistant_worker.session import AssistantVoiceSession, resolve_instructions
from voice_infra import BackendRegistry
from voice_infra.config import BACKENDS_ENV

from _worker_fakes import FakeAgentSession, FakeJobContext, FakeRoom, conversation_item, participant, user_transcribed

SPEC = {"practice": {"base_url_env": "PRACTICE_URL", "secret_env": "PRACTICE_SECRET", "secret_header": "X-S", "slot_release_path": "/r", "slot_extend_path": "/e", "slot_payload_key": "room_name"}}
METADATA = json.dumps({"session_id": "unified_1", "backend": "practice", "candidate_ref": "user-1"})


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv(BACKENDS_ENV, json.dumps(SPEC))
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    FakeAgentSession.instances.clear()


class _FakeAgent(FakeAgentSession):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.replies: list[dict] = []
        self.current_agent = MagicMock()

    def generate_reply(self, **kwargs):
        self.replies.append(kwargs)
        fut = asyncio.get_event_loop().create_future()
        fut.set_result(None)
        return fut


@pytest.fixture
def fake_agent(monkeypatch):
    """Replace agent construction with a fake session; record the instructions and tools."""
    builds: list[dict] = []

    def build(**kwargs):
        agent = _FakeAgent()
        builds.append(kwargs)
        gli = kwargs["gpt_live_instructions"]
        return AgentBuild(session=agent, definition={"instructions": kwargs["pipeline_instructions"], "tools": kwargs["pipeline_tools"]}, runtime=kwargs["runtime"], opening_instruction=gli.opening if gli else None)

    monkeypatch.setattr(session_module, "build_assistant_agent", build)
    monkeypatch.setattr(session_module, "build_assistant_llm", lambda wt: f"llm:{wt}")
    monkeypatch.setattr(session_module, "build_assistant_tts", lambda wt, voice_help_intent=None: f"tts:{wt}:{voice_help_intent}")
    monkeypatch.setattr(session_module, "ConversationLatencyTracker", lambda **kw: MagicMock())
    monkeypatch.setattr(session_module, "build_room_options", lambda **kw: kw)
    monkeypatch.setattr(session_module, "build_anthropic_computer_tool", lambda ctx, wt: "computer-tool")
    monkeypatch.setattr(session_module, "build_offer_navigation_modes_tool", lambda ctx: "nav-mode-tool")
    return builds


def _run(bootstrap: AssistantSession, *, joined: str = "user-1"):
    room = FakeRoom(local_identity="agent-me")
    if joined:
        room.join(joined)
    ctx = FakeJobContext(room, metadata=METADATA)
    ctx.proc = MagicMock()
    ctx.proc.userdata = {}
    voice = AssistantVoiceSession(BackendRegistry.from_env(), candidate_timeout=0.05)
    with patch.object(session_module, "fetch_bootstrap", return_value=bootstrap):
        result = asyncio.run(voice.entrypoint(ctx))
    return voice, ctx, result


def test_help_session_on_the_pipeline_with_screen_guidance(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", extras={"screen_ui_guidance": True, "voice_help_intent": "guide"})
    voice, ctx, result = _run(bootstrap)
    assert result is bootstrap and voice.runtime is VoiceRuntime.PIPELINE
    build = fake_agent[0]
    assert build["pipeline_tools"][0] is session_module.search_help_faqs
    assert build["pipeline_tools"][1:] == ["nav-mode-tool", "computer-tool"]
    assert "HANDS-OFF NAVIGATION" in build["pipeline_instructions"]
    assert build["max_tool_steps"] == 10 and build["pipeline_llm"] == "llm:help" and build["pipeline_tts"] == "tts:help:guide"
    agent = FakeAgentSession.instances[-1]
    assert agent.said[0][0].startswith("Hi, I'm Athena")
    assert ctx.proc.userdata["navigation_mode"] == "guide"
    assert len(ctx.shutdown_callbacks) >= 2  # cloud slot release + transcript delivery


def test_help_transcript_is_captured_and_delivered_once(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", extras={"voice_help_intent": "guide"})
    post = AsyncMock(return_value=200)
    with patch("livekit_assistant_worker.transcript.post_json", post):
        room = FakeRoom(local_identity="agent-me")
        room.join("user-1")
        ctx = FakeJobContext(room, metadata=METADATA)
        ctx.proc = MagicMock(); ctx.proc.userdata = {}
        voice = AssistantVoiceSession(BackendRegistry.from_env(), candidate_timeout=0.05)

        async def scenario():
            with patch.object(session_module, "fetch_bootstrap", return_value=bootstrap):
                await voice.entrypoint(ctx)
            agent = FakeAgentSession.instances[-1]
            agent.emit("user_input_transcribed", user_transcribed("Where is AI Practice?"))
            agent.emit("conversation_item_added", conversation_item("In the left navigation."))
            room.emit("participant_disconnected", participant("user-1"))
            await asyncio.sleep(0)
            for cb in ctx.shutdown_callbacks:
                await cb()

        asyncio.run(scenario())
    assert post.await_count == 1
    payload = post.call_args.args[1]
    assert [(m["role"], m["message"]) for m in payload["transcript"]["messages"]] == [("user", "Where is AI Practice?"), ("assistant", "In the left navigation.")]
    assert post.call_args.args[0] == "https://api.test/api/worker/assistant-sessions/unified_1/transcript"


def test_nav_mode_choice_from_the_browser_switches_mode_and_prompts_the_model(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", extras={"screen_ui_guidance": True})
    voice, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        packet = MagicMock(data=json.dumps({"type": "nav_mode_choice", "mode": "automate"}).encode(), participant=participant("user-1"))
        ctx.room.emit("data_received", packet)
        await asyncio.sleep(0)

    asyncio.run(scenario())
    assert ctx.proc.userdata["navigation_mode"] == "automate"
    assert "Navigate for me" in agent.replies[-1]["user_input"]


def test_onboarding_opens_with_a_generated_reply_and_rebuilds_on_scene_change(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", extras={"onboarding_phase": "intro", "user_name": "amina"})
    voice, ctx, _ = _run(bootstrap)
    build = fake_agent[0]
    assert "INTRODUCTION phase" in build["pipeline_instructions"] and "Doctor Amina" in build["pipeline_instructions"]
    agent = FakeAgentSession.instances[-1]
    assert agent.said == [] and agent.replies[0] == {"allow_interruptions": True}

    async def scenario():
        packet = MagicMock(data=json.dumps({"type": "scene_change", "phase": "demo", "question": "How would you respond?", "patientLine": "I'm scared."}).encode())
        ctx.room.emit("data_received", packet)
        await asyncio.sleep(0)

    asyncio.run(scenario())
    assert "The patient says: 'I'm scared.'" in agent.replies[-1]["instructions"]
    assert agent.replies[-1]["user_input"].startswith("[New scene started")


def test_dashboard_and_doctor_use_backend_rendered_instructions(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="dashboard", candidate_ref="user-1", instructions="Rendered dashboard prompt.", greeting="Custom greeting.")
    _, _, _ = _run(bootstrap)
    assert fake_agent[-1]["pipeline_instructions"] == "Rendered dashboard prompt." and fake_agent[-1]["max_tool_steps"] == 5
    assert FakeAgentSession.instances[-1].said[0][0] == "Custom greeting."
    doctor = AssistantSession(session_id="unified_1", worker_type="athena-doctor", candidate_ref="user-1")
    assert resolve_instructions(doctor) == session_module.DEFAULT_INSTRUCTIONS


def test_faq_help_with_credentials_runs_on_gpt_live(fake_agent, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(session_module, "register_gpt_live_session_policy", MagicMock())
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", extras={"voice_help_intent": "faq"})
    voice, _, _ = _run(bootstrap)
    assert voice.runtime is VoiceRuntime.GPT_LIVE
    assert fake_agent[0]["gpt_live_instructions"] is not None
    session_module.register_gpt_live_session_policy.assert_called_once()
    agent = FakeAgentSession.instances[-1]
    assert agent.said == [] and "Athena" in agent.replies[0]["instructions"]


def test_no_client_within_the_wait_ends_the_job(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1")
    _, _, result = _run(bootstrap, joined="")
    assert result is None and fake_agent == []


def test_bad_metadata_never_connects(fake_agent) -> None:
    ctx = FakeJobContext(metadata='{"backend": "practice"}')
    assert asyncio.run(AssistantVoiceSession(BackendRegistry.from_env()).entrypoint(ctx)) is None
    assert ctx.connect_calls == []
