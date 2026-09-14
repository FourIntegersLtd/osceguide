"""GPT-Live limits, tool progress, the computer tool, and transcript delivery."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from livekit_assistant_worker import transcript as transcript_module
from livekit_assistant_worker.gpt_live_policy import (
    HARD_WARNING_SECONDS, IDLE_GRACE_SECONDS, IDLE_WARNING_SECONDS, MAX_SECONDS,
    GptLiveSessionController, GptLiveSessionPolicyConfig, SessionEndReason, serialize_usage,
)
from livekit_assistant_worker.help_corpus import HelpCorpus
from livekit_assistant_worker.tools.help_search import run_search_help_faqs
from livekit_assistant_worker.transcript import TranscriptDelivery, TranscriptRecorder
from livekit_assistant_worker.ui_guidance.base_computer_toolset import BaseComputerTool
from osce_assessment.contracts import MessageRole
from voice_infra import BackendEndpoints

ENDPOINTS = BackendEndpoints(label="practice", base_url_env="PRACTICE_URL", secret_env="PRACTICE_SECRET", secret_header="X-S", slot_release_path="/r", slot_extend_path="/e", slot_payload_key="room_name")


def _agent_and_ctx():
    ctx = MagicMock()
    ctx.room.local_participant.publish_data = AsyncMock()
    ctx.shutdown = MagicMock()
    agent = MagicMock()
    agent.current_agent.duplex_session = MagicMock()
    agent.shutdown = MagicMock()
    agent.usage = None
    return agent, ctx


def test_policy_defaults_match_the_legacy_limits_and_come_from_env(monkeypatch) -> None:
    assert (MAX_SECONDS, HARD_WARNING_SECONDS, IDLE_WARNING_SECONDS, IDLE_GRACE_SECONDS) == (300, 60, 60, 30)
    assert GptLiveSessionPolicyConfig.from_env() == GptLiveSessionPolicyConfig()
    monkeypatch.setenv("GPT_LIVE_MAX_SECONDS", "600")
    monkeypatch.setenv("GPT_LIVE_IDLE_GRACE_SECONDS", "not-a-number")
    config = GptLiveSessionPolicyConfig.from_env()
    assert config.max_seconds == 600 and config.idle_grace_seconds == IDLE_GRACE_SECONDS


def test_hard_timeout_closes_session() -> None:
    agent, ctx = _agent_and_ctx()
    controller = GptLiveSessionController(ctx=ctx, agent=agent, session_id="room-1", worker_type="help", config=GptLiveSessionPolicyConfig(max_seconds=0.05, hard_warning_seconds=0, idle_warning_seconds=999, idle_grace_seconds=999))

    async def run() -> None:
        with patch.object(controller, "_post_session_completion", new=AsyncMock()):
            controller.attach()
            await asyncio.sleep(0.1)
            if controller.end_reason is None:
                await controller.close(SessionEndReason.HARD_TIMEOUT)

    asyncio.run(run())
    agent.shutdown.assert_called_once()
    ctx.shutdown.assert_called_once()


def test_idle_timeout_after_warning() -> None:
    agent, ctx = _agent_and_ctx()
    controller = GptLiveSessionController(ctx=ctx, agent=agent, session_id="room-2", worker_type="help", config=GptLiveSessionPolicyConfig(max_seconds=60, hard_warning_seconds=30, idle_warning_seconds=0.05, idle_grace_seconds=0.05))

    async def run() -> None:
        with patch.object(controller, "_post_session_completion", new=AsyncMock()):
            controller.attach()
            await asyncio.sleep(0.75)

    asyncio.run(run())
    assert controller.end_reason is SessionEndReason.IDLE_TIMEOUT


def test_completion_is_posted_to_the_dispatching_backend(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s")
    agent, ctx = _agent_and_ctx()
    controller = GptLiveSessionController(ctx=ctx, agent=agent, session_id="room-3", worker_type="help", endpoints=ENDPOINTS)
    post = AsyncMock(return_value=200)
    with patch("livekit_assistant_worker.gpt_live_policy.post_json", post):
        asyncio.run(controller.close(SessionEndReason.USER_DISCONNECT))
        asyncio.run(controller._report_usage_on_shutdown())
    url, payload = post.call_args.args
    assert url == "https://api.test/api/worker/sessions/room-3/complete"
    assert payload["end_reason"] == "user_disconnect" and payload["worker_type"] == "help" and payload["usage"] == {}
    assert post.call_args.kwargs["headers"] == {"X-S": "s"}
    assert serialize_usage(None) == {} and serialize_usage("x") == {"value": "x"}


def test_search_help_faqs_calls_update_and_filler() -> None:
    async def run() -> None:
        ctx = MagicMock()
        ctx.update = AsyncMock()
        filler_cm = AsyncMock()
        filler_cm.__aenter__ = AsyncMock(return_value=None)
        filler_cm.__aexit__ = AsyncMock(return_value=None)
        ctx.with_filler = MagicMock(return_value=filler_cm)
        corpus = HelpCorpus.model_validate({"entries": [{"section": "Nav", "question": "Where is AI Practice?", "answer": "Left navigation."}]})
        result = await run_search_help_faqs(ctx, corpus, "Where is AI Practice?")
        ctx.update.assert_awaited_once_with("Let me check the help articles for your question.")
        assert ctx.with_filler.call_args.kwargs["max_steps"] is None
        assert "AI Practice" in result

    asyncio.run(run())


class _StubComputerTool(BaseComputerTool):
    async def _analyse_screenshot(self, jpeg_b64: str, media_type: str) -> str:
        return "[]"


def test_computer_screenshot_uses_update_and_unlimited_filler() -> None:
    async def run() -> None:
        tool = _StubComputerTool.__new__(_StubComputerTool)
        tool._LOG_PREFIX = "TEST"
        tool._worker_type = "help"
        tool._is_rate_limited = lambda: False  # type: ignore[method-assign]
        tool._set_tool_running = AsyncMock()  # type: ignore[method-assign]
        tool._capture_screenshot = AsyncMock(return_value=("b64", "image/jpeg"))  # type: ignore[method-assign]
        tool._analyse_screenshot = AsyncMock(return_value='[{"type": "text", "text": "ok"}]')  # type: ignore[method-assign]
        run_ctx = MagicMock()
        run_ctx.update = AsyncMock()
        filler_cm = AsyncMock()
        filler_cm.__aenter__ = AsyncMock(return_value=None)
        filler_cm.__aexit__ = AsyncMock(return_value=None)
        run_ctx.with_filler = MagicMock(return_value=filler_cm)
        await BaseComputerTool.handle(tool, {"action": "screenshot"}, run_ctx)
        assert run_ctx.update.await_count == 2
        assert run_ctx.with_filler.call_args.kwargs["max_steps"] is None
        tool._capture_screenshot.assert_awaited_once()

    asyncio.run(run())


def test_transcript_is_delivered_once_with_retries(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s")
    recorder = TranscriptRecorder("unified_1")
    recorder.add(MessageRole.USER, "Where is AI Practice?")
    recorder.add(MessageRole.ASSISTANT, "In the left navigation.")
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    delivery = TranscriptDelivery(ENDPOINTS, recorder, worker_type="help", candidate_ref="u1", sleep=sleep)
    post = AsyncMock(side_effect=[503, 200])
    with patch.object(transcript_module, "post_json", post):
        assert asyncio.run(delivery.deliver_once()) is True
        assert asyncio.run(delivery.deliver_once()) is True  # already delivered: no new POST
    assert post.await_count == 2 and sleeps == [2.0]
    url, payload = post.call_args.args
    assert url == "https://api.test/api/worker/assistant-sessions/unified_1/transcript"
    assert payload["worker_type"] == "help" and payload["candidate_ref"] == "u1"
    assert [m["message"] for m in payload["transcript"]["messages"]] == ["Where is AI Practice?", "In the left navigation."]
    assert payload["transcript"]["messages"][1]["seq"] == 1


def test_a_failed_delivery_stays_undelivered_for_the_other_path(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    recorder = TranscriptRecorder("unified_1")

    async def sleep(_: float) -> None:
        return None

    delivery = TranscriptDelivery(ENDPOINTS, recorder, worker_type="help", candidate_ref="u1", sleep=sleep)
    with patch.object(transcript_module, "post_json", AsyncMock(return_value=500)):
        assert asyncio.run(delivery.deliver_once()) is False
    assert delivery.delivered is False
