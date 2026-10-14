"""One assistant job against fakes, per session type."""

from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from livekit_assistant_worker import session as session_module
from livekit_assistant_worker.agent_factory import AgentBuild
from livekit_assistant_worker.bootstrap import AssistantSession, GPTLiveInstructions
from livekit_assistant_worker.runtime_policy import VoiceRuntime
from livekit_assistant_worker.session import AssistantVoiceSession
from voice_infra import BackendRegistry
from voice_infra.config import BACKENDS_ENV

from _worker_fakes import FakeAgentSession, FakeJobContext, FakeRoom, conversation_item, participant, user_transcribed

SPEC = {"practice": {"base_url_env": "PRACTICE_URL", "secret_env": "PRACTICE_SECRET", "secret_header": "X-S", "slot_release_path": "/r", "slot_extend_path": "/e", "slot_payload_key": "room_name"}}
METADATA = json.dumps({"session_id": "unified_1", "backend": "practice", "candidate_ref": "user-1"})
GPT_LIVE = GPTLiveInstructions(voice="You are the voice.", backend="You are the delegate.", opening="Introduce yourself.")


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
        self.interrupts = 0
        self.current_agent = MagicMock()
        self.current_agent.update_instructions = AsyncMock()

    def _done(self):
        fut = asyncio.get_event_loop().create_future()
        fut.set_result(None)
        return fut

    def generate_reply(self, **kwargs):
        self.replies.append(kwargs)
        return self._done()

    def interrupt(self, **_kwargs):
        self.interrupts += 1
        return self._done()


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
    monkeypatch.setattr(session_module, "build_vision_llm", lambda: "llm:vision")
    monkeypatch.setattr(session_module, "build_llm", lambda tier: f"llm:{tier}")
    monkeypatch.setattr(session_module, "build_tts", lambda role: f"tts:{role}")
    monkeypatch.setattr(session_module, "ConversationLatencyTracker", lambda **kw: MagicMock())
    monkeypatch.setattr(session_module, "build_room_options", lambda **kw: kw)
    def _computer_toolset(ctx, worker_type, navigation):
        toolset = MagicMock()
        toolset.as_function_tool.return_value = ("computer-tool", navigation)
        return toolset

    monkeypatch.setattr(session_module, "build_computer_toolset", _computer_toolset)
    monkeypatch.setattr(session_module, "build_offer_navigation_modes_tool", lambda ctx: "nav-mode-tool")
    monkeypatch.setattr(session_module, "build_check_time_tool", lambda clock: "check-time-tool")
    monkeypatch.setattr(session_module, "build_remote_tools", lambda endpoints, session_id, specs, publish: [f"remote:{endpoints.label}:{session_id}:{s.name}" for s in specs])
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
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Rendered help prompt, FAQ included.", greeting="Hi, I'm the help assistant.", extras={"screen_ui_guidance": True, "voice_help_intent": "guide"})
    voice, ctx, result = _run(bootstrap)
    assert result is bootstrap and voice.runtime is VoiceRuntime.PIPELINE
    build = fake_agent[0]
    # No FAQ tool: the answers arrive inside the instructions. The computer tool reads the session's own state.
    assert build["pipeline_tools"] == ["nav-mode-tool", ("computer-tool", voice.navigation)]
    # The agent needs the toolset itself, not just its tool: inline pointer tags in
    # the reply are published through it as the words are spoken.
    assert build["guidance_toolset"] is voice.guidance
    assert build["pipeline_instructions"] == "Rendered help prompt, FAQ included."
    assert build["max_tool_steps"] == 10 and build["pipeline_llm"] == "llm:vision" and build["pipeline_tts"] == "tts:tutor"
    agent = FakeAgentSession.instances[-1]
    assert agent.said[0][0] == "Hi, I'm the help assistant."
    assert voice.navigation.mode == "guide"
    assert len(ctx.shutdown_callbacks) >= 2  # cloud slot release + transcript delivery


def test_help_transcript_is_captured_and_delivered_once(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Help.", extras={"voice_help_intent": "guide"})
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
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Help.", extras={"screen_ui_guidance": True})
    voice, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        packet = MagicMock(data=json.dumps({"type": "nav_mode_choice", "mode": "automate"}).encode(), participant=participant("user-1"))
        ctx.room.emit("data_received", packet)
        await asyncio.sleep(0)

    asyncio.run(scenario())
    assert voice.navigation.mode == "automate"
    assert "Navigate for me" in agent.replies[-1]["user_input"]


def test_a_help_session_without_a_backend_greeting_lets_the_model_open(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Help.")
    _run(bootstrap)
    agent = FakeAgentSession.instances[-1]
    assert agent.said == [] and agent.replies[0] == {"allow_interruptions": True}


def test_a_mode_without_screen_guidance_gets_no_tools(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="dashboard", candidate_ref="user-1", instructions="Coach.")
    _run(bootstrap)
    assert fake_agent[0]["pipeline_tools"] == []


TOOLS = [
    {"name": "lookup_notes", "description": "Find a note.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "show_item", "description": "Show something.", "parameters": {"type": "object", "properties": {"ref": {"type": "string"}}}},
]


def test_a_dashboard_session_registers_the_backends_tools_and_delivers_its_turns(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="dashboard", candidate_ref="user-1", instructions="Rendered tutor prompt.", greeting="Welcome back.", tools=TOOLS)
    voice, ctx, _ = _run(bootstrap)
    build = fake_agent[0]
    assert build["pipeline_tools"] == ["remote:practice:unified_1:lookup_notes", "remote:practice:unified_1:show_item"]
    assert build["pipeline_llm"] == "llm:tutor" and build["max_tool_steps"] == 5
    assert voice.recorder is not None and voice.delivery is not None, "the turns go back to the backend for summarising"
    assert len(ctx.shutdown_callbacks) >= 2  # cloud slot release + transcript delivery


@pytest.mark.parametrize(
    ("worker_type", "extras", "model"),
    [("help", {"voice_help_intent": "faq"}, "llm:vision"), ("help", {"voice_help_intent": "guide"}, "llm:vision"), ("onboarding", {}, "llm:vision"), ("dashboard", {}, "llm:tutor"), ("consulting-doctor", {}, "llm:tutor")],
)
def test_every_session_type_gets_its_model_tier_and_the_one_tutor_voice_chain(fake_agent, worker_type, extras, model) -> None:
    """The model tier comes from the mode table; the voice never does. FAQ help used to put OpenAI first,
    so a fallback changed the voice mid-session (C-36)."""
    _run(AssistantSession(session_id="unified_1", worker_type=worker_type, candidate_ref="user-1", instructions="Rendered.", extras=extras))
    assert fake_agent[0]["pipeline_llm"] == model
    assert fake_agent[0]["pipeline_tts"] == "tts:tutor"


def test_a_mode_that_does_not_load_tools_ignores_any_the_backend_sends(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.", tools=TOOLS)
    _run(bootstrap)
    assert fake_agent[0]["pipeline_tools"] == []


def test_onboarding_opens_with_a_generated_reply_and_asks_the_backend_for_each_scene(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro scene, rendered by the backend.")
    voice, ctx, _ = _run(bootstrap)
    assert fake_agent[0]["pipeline_instructions"] == "Intro scene, rendered by the backend."
    agent = FakeAgentSession.instances[-1]
    assert agent.said == [] and agent.replies[0] == {"allow_interruptions": True}

    rendered = MagicMock(return_value="Demo scene, rendered by the backend.")

    async def scenario():
        packet = MagicMock(data=json.dumps({"type": "scene_change", "phase": "demo", "question": "How would you respond?", "patientLine": "I'm scared."}).encode())
        with patch.object(session_module, "fetch_scene_instructions", rendered):
            ctx.room.emit("data_received", packet)
            await asyncio.sleep(0.05)

    asyncio.run(scenario())
    endpoints, session_id, scene = rendered.call_args.args
    assert (endpoints.label, session_id) == ("practice", "unified_1")
    assert scene == {"phase": "demo", "question": "How would you respond?", "patientLine": "I'm scared."}
    assert agent.replies[-1] == {"instructions": "Demo scene, rendered by the backend.", "user_input": session_module.handlers.SCENE_STARTED_INPUT}


def test_a_new_scene_cuts_off_whatever_athena_is_still_saying(fake_agent) -> None:
    """Clicking through mid-intro must stop the intro, not queue the scene behind it."""
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        with patch.object(session_module, "fetch_scene_instructions", MagicMock(return_value="Demo scene.")):
            ctx.room.emit("data_received", MagicMock(data=json.dumps({"type": "scene_change", "phase": "demo", "patientLine": "I'm scared."}).encode()))
            await asyncio.sleep(0.05)

    asyncio.run(scenario())
    assert agent.interrupts == 1
    assert agent.replies[-1]["instructions"] == "Demo scene."


def test_a_new_scene_becomes_what_athena_answers_from(fake_agent) -> None:
    """C-53: a scene's script must outlive its introduction, or the learner's answer is met with the intro again."""
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        with patch.object(session_module, "fetch_scene_instructions", MagicMock(return_value="Demo scene.")):
            ctx.room.emit("data_received", _packet("scene_change", phase="demo", patientLine="I'm scared."))
            await asyncio.sleep(0.05)

    asyncio.run(scenario())
    agent.current_agent.update_instructions.assert_awaited_once_with("Demo scene.")


def test_two_scene_changes_in_quick_succession_speak_only_the_second(fake_agent) -> None:
    """C-53: a slow render of the scene the learner already left must not land after the current one."""
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    def render(_endpoints, _session_id, scene):
        time.sleep(0.1 if scene["phase"] == "intro" else 0.01)
        return f"{scene['phase']} scene."

    async def scenario():
        with patch.object(session_module, "fetch_scene_instructions", render):
            ctx.room.emit("data_received", _packet("scene_change", phase="intro"))
            ctx.room.emit("data_received", _packet("scene_change", phase="demo", patientLine="I'm scared."))
            await asyncio.sleep(0.2)

    asyncio.run(scenario())
    assert [reply.get("instructions") for reply in agent.replies[1:]] == ["demo scene."]
    agent.current_agent.update_instructions.assert_awaited_once_with("demo scene.")


def test_athena_still_thinking_after_the_wait_says_so_and_asks_again(fake_agent, monkeypatch) -> None:
    """C-54: an off-script answer must never leave her silent on "thinking"."""
    monkeypatch.setattr(session_module.handlers, "STALL_TIMEOUT_S", 0.02)
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        agent.emit("agent_state_changed", SimpleNamespace(new_state="thinking"))
        await asyncio.sleep(0.08)

    asyncio.run(scenario())
    assert agent.interrupts == 1
    assert agent.replies[-1] == {"instructions": session_module.handlers.STALL_INSTRUCTION}


def test_athena_who_starts_speaking_in_time_is_left_alone(fake_agent, monkeypatch) -> None:
    """C-54: leaving "thinking" before the wait ends disarms the watchdog, so no recovery reply."""
    monkeypatch.setattr(session_module.handlers, "STALL_TIMEOUT_S", 0.05)
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        agent.emit("agent_state_changed", SimpleNamespace(new_state="thinking"))
        await asyncio.sleep(0.01)
        agent.emit("agent_state_changed", SimpleNamespace(new_state="speaking"))
        await asyncio.sleep(0.1)

    asyncio.run(scenario())
    assert agent.interrupts == 0
    assert len(agent.replies) == 1  # only the opening


def test_the_same_scene_announced_twice_is_only_read_once(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]
    rendered = MagicMock(return_value="Demo scene.")
    scene = json.dumps({"type": "scene_change", "phase": "demo", "question": "How would you respond?", "patientLine": "I'm scared."}).encode()

    async def scenario():
        with patch.object(session_module, "fetch_scene_instructions", rendered):
            ctx.room.emit("data_received", MagicMock(data=scene))
            ctx.room.emit("data_received", MagicMock(data=scene))
            await asyncio.sleep(0.05)
            # A genuinely different scene still gets through.
            ctx.room.emit("data_received", MagicMock(data=json.dumps({"type": "scene_change", "phase": "demo", "question": "And now?", "patientLine": "I feel worse."}).encode()))
            await asyncio.sleep(0.05)

    asyncio.run(scenario())
    assert rendered.call_count == 2
    assert len(agent.replies) == 3  # the opening, plus one per distinct scene


def test_a_scene_the_backend_cannot_render_leaves_the_current_scene_running(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        with patch.object(session_module, "fetch_scene_instructions", MagicMock(side_effect=RuntimeError("down"))):
            ctx.room.emit("data_received", MagicMock(data=json.dumps({"type": "scene_change", "phase": "demo"}).encode()))
            await asyncio.sleep(0.05)

    asyncio.run(scenario())
    assert len(agent.replies) == 1  # only the opening; no reply on a scene that was not rendered


def _packet(kind: str, **fields) -> MagicMock:
    return MagicMock(data=json.dumps({"type": kind, **fields}).encode())


def test_pause_stops_athena_and_holds_the_next_scene_until_resume(fake_agent) -> None:
    """Paused means silent: what she was saying stops, and a scene clicked to meanwhile waits."""
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]
    rendered = MagicMock(return_value="Demo scene.")

    async def paused():
        with patch.object(session_module, "fetch_scene_instructions", rendered):
            ctx.room.emit("data_received", _packet("pause"))
            await asyncio.sleep(0.02)
            ctx.room.emit("data_received", _packet("scene_change", phase="demo", patientLine="I'm scared."))
            await asyncio.sleep(0.05)

    asyncio.run(paused())
    assert agent.interrupts == 1
    assert rendered.call_count == 0
    assert len(agent.replies) == 1  # only the opening

    async def resumed():
        with patch.object(session_module, "fetch_scene_instructions", rendered):
            ctx.room.emit("data_received", _packet("resume"))
            await asyncio.sleep(0.05)

    asyncio.run(resumed())
    assert rendered.call_count == 1
    assert agent.replies[-1]["instructions"] == "Demo scene."


def test_resume_with_no_scene_waiting_says_nothing_new(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="onboarding", candidate_ref="user-1", instructions="Intro.")
    _, ctx, _ = _run(bootstrap)
    agent = FakeAgentSession.instances[-1]

    async def scenario():
        ctx.room.emit("data_received", _packet("pause"))
        ctx.room.emit("data_received", _packet("resume"))
        await asyncio.sleep(0.05)

    asyncio.run(scenario())
    assert len(agent.replies) == 1


def test_dashboard_and_doctor_use_backend_rendered_instructions(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="dashboard", candidate_ref="user-1", instructions="Rendered dashboard prompt.", greeting="Custom greeting.")
    _, _, _ = _run(bootstrap)
    assert fake_agent[-1]["pipeline_instructions"] == "Rendered dashboard prompt." and fake_agent[-1]["max_tool_steps"] == 5
    assert FakeAgentSession.instances[-1].said[0][0] == "Custom greeting."


PACING = {
    "total_seconds": 720,
    "marks": [{"at_seconds": 360, "note": "[Notice: half the time has gone.]"}],
    "phases": [{"until_seconds": 360, "label": "history taking"}, {"until_seconds": 720, "label": "the close"}],
}


def test_a_paced_session_gets_the_time_tool_and_a_clock_that_stops_on_shutdown(fake_agent) -> None:
    bootstrap = AssistantSession(
        session_id="unified_1", worker_type="consulting-doctor", candidate_ref="user-1",
        instructions="Rendered consultation prompt.", extras={"pacing": PACING},
    )
    voice, ctx, _ = _run(bootstrap)
    assert fake_agent[-1]["pipeline_tools"] == ["check-time-tool"]
    assert voice.clock is not None and voice.clock.elapsed() is not None, "the clock starts when the consultation opens"
    assert voice.clock.cancel in ctx.shutdown_callbacks, "and it is torn down with the job"


def test_a_backend_that_sends_no_clock_gets_the_behaviour_it_had_before(fake_agent) -> None:
    """The worker may deploy ahead of the backend; a missing plan is not an error."""
    bootstrap = AssistantSession(session_id="unified_1", worker_type="consulting-doctor", candidate_ref="user-1", instructions="Rendered consultation prompt.")
    voice, _, _ = _run(bootstrap)
    assert fake_agent[-1]["pipeline_tools"] == []
    assert voice.clock is None


def test_faq_help_with_credentials_runs_on_gpt_live(fake_agent, monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_GPT_LIVE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(session_module, "register_gpt_live_session_policy", MagicMock())
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Help.", gpt_live=GPT_LIVE, extras={"voice_help_intent": "faq"})
    voice, _, _ = _run(bootstrap)
    assert voice.runtime is VoiceRuntime.GPT_LIVE
    assert fake_agent[0]["gpt_live_instructions"] is GPT_LIVE
    session_module.register_gpt_live_session_policy.assert_called_once()
    agent = FakeAgentSession.instances[-1]
    assert agent.said == [] and agent.replies[0]["instructions"] == "Introduce yourself."


def test_faq_help_stays_on_the_pipeline_when_the_backend_sends_no_gpt_live_instructions(fake_agent, monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_GPT_LIVE_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Help.", extras={"voice_help_intent": "faq"})
    voice, _, _ = _run(bootstrap)
    assert voice.runtime is VoiceRuntime.PIPELINE and fake_agent[0]["gpt_live_instructions"] is None


def test_no_client_within_the_wait_ends_the_job(fake_agent) -> None:
    bootstrap = AssistantSession(session_id="unified_1", worker_type="help", candidate_ref="user-1", instructions="Help.")
    _, _, result = _run(bootstrap, joined="")
    assert result is None and fake_agent == []


def test_bad_metadata_never_connects(fake_agent) -> None:
    ctx = FakeJobContext(metadata='{"backend": "practice"}')
    assert asyncio.run(AssistantVoiceSession(BackendRegistry.from_env()).entrypoint(ctx)) is None
    assert ctx.connect_calls == []
