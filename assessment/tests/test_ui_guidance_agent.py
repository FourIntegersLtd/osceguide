"""The agent that strips inline pointer tags out of its own reply."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from livekit.agents import Agent

from livekit_assistant_worker.ui_guidance.agent import GuidanceAgent
from livekit_assistant_worker.ui_guidance.contracts import POINTER_MESSAGE_TYPE, RPC_METHOD_SCREENSHOT_CHUNKED
from livekit_assistant_worker.ui_guidance.navigation import NavigationModeState
from livekit_assistant_worker.ui_guidance.toolset import ComputerToolset

from _worker_fakes import FakeJobContext, FakeRoom

META = {"totalChunks": 1, "viewportWidth": 1600, "viewportHeight": 900, "captureWidth": 800, "captureHeight": 450}
REPLY = ["Tap ", "[POINT:40", "0,225:AI Practice]", " AI Practice, then say next."]
SPOKEN = "Tap AI Practice, then say next."


@pytest.fixture
def guidance() -> tuple[GuidanceAgent, FakeRoom, ComputerToolset]:
    room = FakeRoom()
    room.join("user-1")
    room.local_participant.rpc_responses[RPC_METHOD_SCREENSHOT_CHUNKED] = lambda payload: (
        room.receive({"type": "sc_chunk", "id": payload["screenshotId"], "i": 0, "n": 1, "d": "img"}) or META
    )
    toolset = ComputerToolset(FakeJobContext(room), "help", NavigationModeState())
    # The pointer is in screenshot pixels, so there has to have been a screenshot.
    asyncio.run(toolset.capture.capture())
    return GuidanceAgent(toolset=toolset, instructions="Help the user."), room, toolset


async def _stream(chunks: list[str]):
    for chunk in chunks:
        yield chunk


def _pointers(room: FakeRoom) -> list[dict[str, Any]]:
    return room.local_participant.messages(POINTER_MESSAGE_TYPE)


def test_the_spoken_text_has_the_tag_removed_and_the_pointer_published(guidance, monkeypatch) -> None:
    agent, room, _ = guidance
    spoken: list[str] = []

    async def capture_tts(_agent, text, _settings):
        async for chunk in text:
            spoken.append(chunk)
        return
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(Agent.default, "tts_node", capture_tts)

    async def run() -> None:
        async for _ in agent.tts_node(_stream(REPLY), None):
            pass

    asyncio.run(run())

    assert "".join(spoken) == SPOKEN
    assert "POINT" not in "".join(spoken)
    pointer = _pointers(room)[-1]
    assert (pointer["x"], pointer["y"], pointer["text"]) == (800, 450, "AI Practice")


def test_the_transcript_loses_the_tag_without_placing_a_second_pointer(guidance) -> None:
    """Both nodes see the same reply; publishing from both would double every highlight."""
    agent, room, _ = guidance
    before = len(_pointers(room))

    async def run() -> list[str]:
        return [chunk async for chunk in agent.transcription_node(_stream(REPLY), None)]

    transcript = "".join(asyncio.run(run()))

    assert transcript == SPOKEN
    assert len(_pointers(room)) == before, "the transcript node must not publish"


def test_a_reply_that_points_at_nothing_passes_straight_through(guidance) -> None:
    agent, room, _ = guidance
    before = len(_pointers(room))

    async def run() -> list[str]:
        return [chunk async for chunk in agent.transcription_node(_stream(["Nothing ", "to point at."]), None)]

    assert "".join(asyncio.run(run())) == "Nothing to point at."
    assert len(_pointers(room)) == before
