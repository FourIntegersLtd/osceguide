"""The assessment worker against a real LiveKit server (see conftest for the env gate)."""

from __future__ import annotations

import asyncio
import uuid

import pytest

from tests.e2e._harness import StubBackend, WorkerProcess, candidate_session, dispatch, new_room

pytestmark = pytest.mark.e2e


@pytest.fixture
def stack(e2e_env):
    """A stub backend and a worker registered under a unique agent name."""
    attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
    backend = StubBackend(attempt_id=attempt_id, candidate_ref="candidate-e2e")
    asyncio.run(backend.start())
    worker = WorkerProcess(agent_name=f"e2e-assessment-{uuid.uuid4().hex[:6]}", backend_url=backend.base_url, env=e2e_env, candidate_timeout_s=20)
    worker.start()
    asyncio.run(asyncio.sleep(8))  # worker registration
    yield backend, worker, e2e_env
    worker.stop()
    asyncio.run(backend.stop())


def _metadata(backend: StubBackend) -> dict:
    return {"attempt_id": backend.attempt_id, "backend": "e2e", "candidate_ref": backend.candidate_ref}


def test_dispatch_streams_turns_and_delivers_the_transcript_once(stack) -> None:
    backend, worker, env = stack
    room = new_room()

    async def scenario():
        await dispatch(env, agent_name=worker.agent_name, room=room, metadata=_metadata(backend))
        await candidate_session(env, room_name=room, identity=backend.candidate_ref, wav_path=env["LIVEKIT_E2E_AUDIO_WAV"], linger_s=20)
        await asyncio.sleep(15)  # delivery after disconnect

    asyncio.run(scenario())
    roles = [c["message"]["role"] for c in backend.chunks]
    assert "user" in roles and "assistant" in roles, backend.chunks
    assert len(backend.completes) == 1
    assert backend.completes[0]["transcript"]["complete"] is True
    assert [m["seq"] for m in backend.completes[0]["transcript"]["messages"]] == list(range(len(backend.completes[0]["transcript"]["messages"])))


def test_a_duplicate_dispatch_leaves_one_agent(stack) -> None:
    backend, worker, env = stack
    room = new_room()

    async def scenario():
        await dispatch(env, agent_name=worker.agent_name, room=room, metadata=_metadata(backend))
        await dispatch(env, agent_name=worker.agent_name, room=room, metadata=_metadata(backend))
        return await candidate_session(env, room_name=room, identity=backend.candidate_ref, wav_path=env["LIVEKIT_E2E_AUDIO_WAV"], linger_s=15)

    agents = asyncio.run(scenario())
    assert len(agents) == 1, agents


def test_no_candidate_means_no_delivery(stack) -> None:
    backend, worker, env = stack
    room = new_room()

    async def scenario():
        await dispatch(env, agent_name=worker.agent_name, room=room, metadata=_metadata(backend))
        await asyncio.sleep(worker.candidate_timeout_s + 10)

    asyncio.run(scenario())
    assert backend.chunks == [] and backend.completes == []
