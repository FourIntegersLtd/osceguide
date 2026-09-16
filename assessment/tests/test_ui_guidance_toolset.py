"""The computer tool: which actions narrate themselves, and what each one does.

The progress policy is the part worth pinning down. A ``ctx.update`` is not free
narration — the first one makes the tool non-blocking, so its result is deferred
to the next idle moment. Putting one on a millisecond-long action delays the very
sentence the user is waiting for, which is the regression these tests exist for.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from livekit.agents.llm import ToolFlag
from livekit.agents.llm.tool_context import get_raw_function_info

from livekit_assistant_worker.ui_guidance import messages
from livekit_assistant_worker.ui_guidance.contracts import (
    DATA_TYPE_GUIDANCE_PROGRESS,
    POINTER_MESSAGE_TYPE,
    PROGRESS_STEP_ACTING,
    PROGRESS_STEP_CAPTURING,
    PROGRESS_STEP_DONE,
    PROGRESS_STEP_READING,
    RPC_METHOD_PERFORM_CLICK,
    RPC_METHOD_SCREENSHOT_CHUNKED,
    RPC_METHOD_SCROLL,
)
from livekit_assistant_worker.ui_guidance.navigation import NavigationModeState
from livekit_assistant_worker.ui_guidance.pointer_tags import PointerTag
from livekit_assistant_worker.ui_guidance.toolset import ComputerToolset

from _worker_fakes import FakeJobContext, FakeRoom

META = {"totalChunks": 1, "viewportWidth": 1600, "viewportHeight": 900, "captureWidth": 800, "captureHeight": 450}


class FakeRunContext:
    """Records the narration the tool asks for."""

    def __init__(self) -> None:
        self.updates: list[str] = []
        self.fillers: list[dict] = []
        self.interruptions_disallowed = False

    async def update(self, message: str, *, template: str | None = None) -> None:
        self.updates.append(message)

    @asynccontextmanager
    async def with_filler(self, source, **kwargs):
        self.fillers.append(kwargs)
        yield

    def disallow_interruptions(self) -> None:
        self.interruptions_disallowed = True


def _toolset(*, mode: str = "guide", chunks: list[str] | None = None) -> tuple[ComputerToolset, FakeRoom, FakeRunContext]:
    room = FakeRoom()
    room.join("user-1")

    def screenshot(payload: dict) -> dict:
        for index, data in enumerate(chunks or ["imagedata"]):
            room.receive({"type": "sc_chunk", "id": payload["screenshotId"], "i": index, "n": len(chunks or ["x"]), "d": data})
        return {**META, "totalChunks": len(chunks or ["x"])}

    room.local_participant.rpc_responses[RPC_METHOD_SCREENSHOT_CHUNKED] = screenshot
    room.local_participant.rpc_responses[RPC_METHOD_PERFORM_CLICK] = {"ok": True, "pathname": "/practice"}
    room.local_participant.rpc_responses[RPC_METHOD_SCROLL] = {"ok": True, "moved": True}

    navigation = NavigationModeState()
    navigation.set(mode)
    return ComputerToolset(FakeJobContext(room), "help", navigation), room, FakeRunContext()


def _handle(toolset: ComputerToolset, run_ctx: FakeRunContext, **arguments) -> str:
    return asyncio.run(toolset.handle(arguments, run_ctx))


def _text(result: str) -> str:
    return " ".join(block.get("text", "") for block in json.loads(result))


def _steps(room: FakeRoom) -> list[str]:
    return [m["step"] for m in room.local_participant.messages(DATA_TYPE_GUIDANCE_PROGRESS)]


# -- the progress policy -------------------------------------------------------


def test_only_the_screenshot_announces_itself() -> None:
    """It is the one action slow enough that silence reads as a dropped call."""
    toolset, _, run_ctx = _toolset()

    _handle(toolset, run_ctx, action="screenshot")

    assert len(run_ctx.updates) == 1 and run_ctx.fillers


@pytest.mark.parametrize(
    "arguments",
    [
        {"action": "show_pointer", "coordinate": [100, 100]},
        {"action": "perform_click", "coordinate": [100, 100]},
        {"action": "scroll", "direction": "down"},
    ],
)
def test_the_fast_actions_stay_blocking_and_say_nothing(arguments) -> None:
    """Announcing these would defer their result to the next idle moment."""
    toolset, _, run_ctx = _toolset(mode="automate")

    _handle(toolset, run_ctx, **arguments)

    assert run_ctx.updates == [] and run_ctx.fillers == []


def test_the_filler_is_capped_so_a_stuck_tool_stops_talking() -> None:
    toolset, _, run_ctx = _toolset()

    _handle(toolset, run_ctx, action="screenshot")

    assert run_ctx.fillers[0]["max_steps"] == 3


# -- the on-screen panel -------------------------------------------------------


def test_the_panel_stays_up_while_the_model_reads_the_screenshot() -> None:
    """The tool has returned by then, so nothing in it can lower the panel."""
    toolset, room, run_ctx = _toolset()

    _handle(toolset, run_ctx, action="screenshot")

    assert _steps(room) == [PROGRESS_STEP_CAPTURING, PROGRESS_STEP_READING]
    assert PROGRESS_STEP_DONE not in _steps(room)


def test_the_panel_comes_down_when_the_agent_speaks() -> None:
    toolset, room, run_ctx = _toolset()
    _handle(toolset, run_ctx, action="screenshot")

    asyncio.run(toolset.progress.done())

    assert _steps(room)[-1] == PROGRESS_STEP_DONE


def test_scrolling_raises_the_panel_too() -> None:
    """It used to be the one action that left the user with no indication at all."""
    toolset, room, run_ctx = _toolset()

    _handle(toolset, run_ctx, action="scroll", direction="down")

    assert _steps(room) == [PROGRESS_STEP_ACTING]


def test_a_capture_that_fails_lowers_the_panel_rather_than_stranding_it() -> None:
    toolset, room, run_ctx = _toolset()
    toolset.capture._chunk_timeout = 0.05
    room.local_participant.rpc_responses[RPC_METHOD_SCREENSHOT_CHUNKED] = {**META, "totalChunks": 4}

    result = _handle(toolset, run_ctx, action="screenshot")

    assert _text(result) == messages.SCREENSHOT_FAILED
    assert _steps(room)[-1] == PROGRESS_STEP_DONE


# -- the actions ---------------------------------------------------------------


def test_a_screenshot_comes_back_as_an_image_the_model_can_read() -> None:
    toolset, _, run_ctx = _toolset(chunks=["abc", "def"])

    blocks = json.loads(_handle(toolset, run_ctx, action="screenshot"))

    assert blocks[0]["type"] == "image" and blocks[0]["source"]["data"] == "abcdef"


def test_the_pointer_lands_in_viewport_pixels() -> None:
    toolset, room, run_ctx = _toolset()
    _handle(toolset, run_ctx, action="screenshot")  # establishes the capture size

    _handle(toolset, run_ctx, action="show_pointer", coordinate=[400, 225], label="AI Practice")

    pointer = room.local_participant.messages(POINTER_MESSAGE_TYPE)[-1]
    assert (pointer["x"], pointer["y"], pointer["text"]) == (800, 450, "AI Practice")


def test_clicking_is_refused_until_the_user_hands_over_the_wheel() -> None:
    toolset, room, run_ctx = _toolset(mode="guide")

    result = _handle(toolset, run_ctx, action="perform_click", coordinate=[10, 10], label="Slides")

    assert _text(result) == messages.CLICK_NEEDS_AUTOMATE
    assert room.local_participant.rpc_calls == []


def test_a_click_in_hands_off_mode_reports_where_it_landed() -> None:
    toolset, room, run_ctx = _toolset(mode="automate")

    result = _handle(toolset, run_ctx, action="perform_click", coordinate=[100, 100], label="Slides")

    assert "/practice" in _text(result)
    assert room.local_participant.rpc_calls[-1]["method"] == RPC_METHOD_PERFORM_CLICK


def test_a_click_finishes_even_if_the_user_says_stop() -> None:
    """Cancelling a synthetic click halfway would leave the page in an unknown state."""
    toolset, _, run_ctx = _toolset(mode="automate")

    _handle(toolset, run_ctx, action="perform_click", coordinate=[100, 100], label="Slides")

    assert run_ctx.interruptions_disallowed is True


def test_a_scroll_that_moved_nothing_says_so() -> None:
    toolset, room, run_ctx = _toolset()
    room.local_participant.rpc_responses[RPC_METHOD_SCROLL] = {"ok": True, "moved": False}

    result = _handle(toolset, run_ctx, action="scroll", direction="down")

    assert "manually" in _text(result)


# -- what the model gets wrong -------------------------------------------------


@pytest.mark.parametrize("action", ["show_pointer", "perform_click"])
def test_a_missing_coordinate_says_so_instead_of_blaming_the_environment(action) -> None:
    """It used to fall through to "not supported", which the model cannot recover from."""
    toolset, _, run_ctx = _toolset(mode="automate")

    result = _handle(toolset, run_ctx, action=action)

    assert _text(result) == messages.COORDINATE_REQUIRED


def test_an_unknown_action_lists_the_ones_that_exist() -> None:
    toolset, _, run_ctx = _toolset()

    result = _handle(toolset, run_ctx, action="type_text")

    assert "screenshot" in _text(result) and "type_text" in _text(result)


def test_a_scroll_without_a_direction_is_told_which_ones_there_are() -> None:
    toolset, _, run_ctx = _toolset()

    assert _text(_handle(toolset, run_ctx, action="scroll")) == messages.SCROLL_NEEDS_DIRECTION


# -- limits --------------------------------------------------------------------


def test_the_call_budget_is_spent_per_session_not_per_process() -> None:
    """A module-level bucket carried one job's spending into the next."""
    first, _, run_ctx = _toolset()
    for _ in range(40):
        _handle(first, run_ctx, action="scroll", direction="down")
    assert _text(_handle(first, run_ctx, action="scroll", direction="down")) == messages.RATE_LIMITED

    second, _, fresh_ctx = _toolset()

    assert _text(_handle(second, fresh_ctx, action="scroll", direction="down")) != messages.RATE_LIMITED


# -- how the tool is declared --------------------------------------------------


def test_the_tool_can_be_stopped_and_will_not_double_fire() -> None:
    toolset, _, _ = _toolset()

    info = get_raw_function_info(toolset.as_function_tool())

    assert ToolFlag.CANCELLABLE in info.flags
    assert info.on_duplicate == "reject"


# -- inline pointer tags -------------------------------------------------------


def test_an_inline_tag_places_the_pointer_through_the_same_path() -> None:
    toolset, room, run_ctx = _toolset()
    _handle(toolset, run_ctx, action="screenshot")

    asyncio.run(toolset.point_at(PointerTag(x=400, y=225, label="Slides")))

    pointer = room.local_participant.messages(POINTER_MESSAGE_TYPE)[-1]
    assert (pointer["x"], pointer["y"], pointer["text"]) == (800, 450, "Slides")


def test_shutdown_takes_the_room_listener_back_off() -> None:
    room = FakeRoom()
    ctx = FakeJobContext(room)
    ComputerToolset(ctx, "help", NavigationModeState())
    assert room.handlers["data_received"]

    for callback in ctx.shutdown_callbacks:
        asyncio.run(callback())

    assert room.handlers["data_received"] == []
