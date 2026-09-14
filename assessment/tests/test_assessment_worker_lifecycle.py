"""One job end to end against fakes: metadata → bootstrap → candidate → runtime → delivery."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from livekit_assessment_worker import session as session_module
from livekit_assessment_worker import sinks
from livekit_assessment_worker.bootstrap import Bootstrap, BootstrapError
from livekit_assessment_worker.session import AssessmentSession
from osce_assessment.contracts import AttemptStatus, MessageRole
from osce_assessment.runtime import FakeInteractionAdapter
from voice_infra import BackendRegistry
from voice_infra.config import BACKENDS_ENV

from _worker_fakes import FakeJobContext, FakeRoom

SPEC = {"practice": {"base_url_env": "PRACTICE_URL", "secret_env": "PRACTICE_SECRET", "secret_header": "X-Practice-Secret",
                     "slot_release_path": "/slot/release", "slot_extend_path": "/slot/extend", "slot_payload_key": "room_name"}}
METADATA = json.dumps({"attempt_id": "attempt-1", "backend": "practice", "candidate_ref": "candidate-42"})
SCRIPT = [(MessageRole.ASSISTANT, "Hi doctor."), (MessageRole.USER, "What brings you in?"), (MessageRole.ASSISTANT, "Chest pain.")]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv(BACKENDS_ENV, json.dumps(SPEC))
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s3cret")


@pytest.fixture
def bootstrap(attempt, scenario) -> Bootstrap:
    profile = attempt.definition.interaction_profile.model_copy(update={"instructions": "You are the patient."})
    rendered = attempt.model_copy(update={"definition": attempt.definition.model_copy(update={"interaction_profile": profile})})
    return Bootstrap(attempt=rendered, scenario=scenario)


@pytest.fixture
def fake_adapter():
    adapter = FakeInteractionAdapter(SCRIPT)
    adapter.init_kwargs = None

    def factory(ctx, **kwargs):
        adapter.init_kwargs = kwargs
        return adapter

    with patch.object(session_module, "LiveKitInteractionAdapter", factory):
        yield adapter


@pytest.fixture
def no_other_agents():
    async def none(*_, **__):
        return []
    with patch.object(session_module, "other_agents_present", none):
        yield


def _session(**kw) -> AssessmentSession:
    return AssessmentSession(BackendRegistry.from_env(), candidate_timeout=kw.pop("candidate_timeout", 0.05), settle=0)


def test_happy_path_delivers_the_transcript_and_stops_before_evaluation(bootstrap, fake_adapter, no_other_agents) -> None:
    room = FakeRoom(local_identity="agent-me")
    room.join("candidate-42-web")
    ctx = FakeJobContext(room, metadata=METADATA)
    post = AsyncMock(return_value=200)
    with patch.object(session_module, "fetch_bootstrap", return_value=bootstrap), patch.object(sinks, "post_json", post):
        outcome = asyncio.run(_session().entrypoint(ctx))

    assert outcome is not None and outcome.ok
    assert outcome.attempt.status is AttemptStatus.INTERACTION_COMPLETE
    assert outcome.result is None
    assert outcome.delivered is True
    assert [m.message for m in outcome.transcript.messages] == ["Hi doctor.", "What brings you in?", "Chest pain."]
    assert outcome.transcript.runtime_label == "livekit"
    # rendered profile passed straight through; greeting spoken; audio pinned to the matched identity
    assert fake_adapter.profiles[0].instructions == "You are the patient."
    assert fake_adapter.greetings == ["Hi doctor."]
    assert fake_adapter.init_kwargs["candidate_identity"] == "candidate-42-web"
    assert fake_adapter.init_kwargs["gender"] == "male"
    # three chunks streamed then one completed transcript, all to the dispatching backend with its secret
    urls = [call.args[0] for call in post.call_args_list]
    assert urls == ["https://api.test/api/worker/attempts/attempt-1/transcript-chunks"] * 3 + ["https://api.test/api/worker/attempts/attempt-1/transcript"]
    assert all(call.kwargs["headers"] == {"X-Practice-Secret": "s3cret"} for call in post.call_args_list)
    assert ctx.connect_calls and ctx.log_context_fields == {"room": "room-1", "attempt": "attempt-1"}
    assert len(ctx.shutdown_callbacks) >= 1  # cloud slot release registered


def test_bad_metadata_never_connects(fake_adapter) -> None:
    ctx = FakeJobContext(metadata='{"backend": "practice"}')
    assert asyncio.run(_session().entrypoint(ctx)) is None
    assert ctx.connect_calls == []


def test_unknown_backend_label_fails_loudly(fake_adapter) -> None:
    ctx = FakeJobContext(metadata=json.dumps({"attempt_id": "a", "backend": "employer"}))
    with pytest.raises(Exception, match="unknown backend 'employer'"):
        asyncio.run(_session().entrypoint(ctx))


def test_another_agent_in_the_room_makes_this_one_leave(bootstrap, fake_adapter) -> None:
    room = FakeRoom(local_identity="agent-me")
    room.join("agent-stale")
    ctx = FakeJobContext(room, metadata=METADATA)

    async def stale(*_, **__):
        return ["agent-stale"]

    with patch.object(session_module, "other_agents_present", stale), patch.object(session_module, "fetch_bootstrap") as fetch:
        assert asyncio.run(_session().entrypoint(ctx)) is None
    fetch.assert_not_called()
    assert fake_adapter.profiles == []


def test_bootstrap_failure_ends_the_job_without_an_interaction(fake_adapter, no_other_agents) -> None:
    ctx = FakeJobContext(metadata=METADATA)
    with patch.object(session_module, "fetch_bootstrap", side_effect=BootstrapError("boom")):
        assert asyncio.run(_session().entrypoint(ctx)) is None
    assert fake_adapter.profiles == []


def test_no_candidate_within_the_wait_ends_the_job_without_delivery(bootstrap, fake_adapter, no_other_agents) -> None:
    ctx = FakeJobContext(metadata=METADATA)
    post = AsyncMock(return_value=200)
    with patch.object(session_module, "fetch_bootstrap", return_value=bootstrap), patch.object(sinks, "post_json", post):
        assert asyncio.run(_session().entrypoint(ctx)) is None
    post.assert_not_called()
    assert fake_adapter.profiles == []


def test_failed_delivery_is_reported_not_swallowed(bootstrap, fake_adapter, no_other_agents) -> None:
    room = FakeRoom()
    room.join("candidate-42")
    ctx = FakeJobContext(room, metadata=METADATA)
    with patch.object(session_module, "fetch_bootstrap", return_value=bootstrap), \
         patch.object(sinks, "post_json", AsyncMock(return_value=503)), \
         patch.object(session_module.AttemptRuntime, "__init__", _immediate_retry_init):
        outcome = asyncio.run(_session().entrypoint(ctx))
    assert outcome is not None
    assert outcome.delivered is False
    assert outcome.ok is False


_original_init = session_module.AttemptRuntime.__init__


def _immediate_retry_init(self, *args, **kwargs):
    from osce_assessment.runtime import RetryPolicy
    kwargs["retry_policy"] = RetryPolicy.immediate()
    _original_init(self, *args, **kwargs)
