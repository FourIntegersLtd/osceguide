"""Capturing the page: an RPC that says how many pieces, and pieces on the data channel."""

from __future__ import annotations

import asyncio

import pytest

from livekit_assistant_worker.ui_guidance.browser import BrowserChannel
from livekit_assistant_worker.ui_guidance.contracts import RPC_METHOD_SCREENSHOT_CHUNKED
from livekit_assistant_worker.ui_guidance.screenshot import ScreenshotCapture

from _worker_fakes import FakeRoom

META = {"totalChunks": 3, "viewportWidth": 1600, "viewportHeight": 900, "captureWidth": 800, "captureHeight": 450, "mediaType": "image/jpeg"}


def _capture(room: FakeRoom, **kwargs) -> ScreenshotCapture:
    capture = ScreenshotCapture(room, BrowserChannel(room), **kwargs)
    capture.attach()
    return capture


def _chunk(index: int, data: str, *, screenshot_id: str, total: int = 3) -> dict:
    return {"type": "sc_chunk", "id": screenshot_id, "i": index, "n": total, "d": data}


def _room_answering_with(chunks: list[str], *, meta: dict | None = None) -> FakeRoom:
    room = FakeRoom()
    room.join("user-1")

    def respond(payload: dict) -> dict:
        for index, data in chunks:
            room.receive(_chunk(index, data, screenshot_id=payload["screenshotId"]))
        return meta or META

    room.local_participant.rpc_responses[RPC_METHOD_SCREENSHOT_CHUNKED] = respond
    return room


def test_the_pieces_are_reassembled_into_one_image() -> None:
    room = _room_answering_with([(0, "aaa"), (1, "bbb"), (2, "ccc")])

    shot = asyncio.run(_capture(room).capture())

    assert shot.image_b64 == "aaabbbccc" and shot.media_type == "image/jpeg"


def test_pieces_arriving_out_of_order_are_put_back_in_order() -> None:
    """The data channel gives no ordering guarantee; the index in each chunk does."""
    room = _room_answering_with([(2, "ccc"), (0, "aaa"), (1, "bbb")])

    shot = asyncio.run(_capture(room).capture())

    assert shot.image_b64 == "aaabbbccc"


def test_the_capture_records_the_sizes_the_pointer_will_need() -> None:
    room = _room_answering_with([(0, "a"), (1, "b"), (2, "c")])
    capture = _capture(room)

    asyncio.run(capture.capture())

    assert capture.viewport.to_viewport(400, 225) == (800, 450)


def test_pieces_that_never_arrive_end_the_capture_rather_than_the_session() -> None:
    room = _room_answering_with([(0, "aaa")])  # promises three, sends one

    shot = asyncio.run(_capture(room, chunk_timeout=0.05).capture())

    assert shot is None


def test_a_malformed_piece_is_discarded_without_stopping_the_others() -> None:
    room = FakeRoom()
    room.join("user-1")

    def respond(payload: dict) -> dict:
        screenshot_id = payload["screenshotId"]
        room.receive({"type": "sc_chunk", "id": screenshot_id, "i": "not-a-number", "d": "junk"})
        for index, data in ((0, "aaa"), (1, "bbb"), (2, "ccc")):
            room.receive(_chunk(index, data, screenshot_id=screenshot_id))
        return META

    room.local_participant.rpc_responses[RPC_METHOD_SCREENSHOT_CHUNKED] = respond

    shot = asyncio.run(_capture(room).capture())

    assert shot.image_b64 == "aaabbbccc"


def test_no_browser_in_the_room_is_reported_not_raised() -> None:
    room = FakeRoom()  # nobody joined

    assert asyncio.run(_capture(room).capture()) is None


def test_chunks_for_a_capture_that_already_finished_are_ignored() -> None:
    room = _room_answering_with([(0, "a"), (1, "b"), (2, "c")])
    capture = _capture(room)
    asyncio.run(capture.capture())

    room.receive(_chunk(0, "late", screenshot_id="gone"))  # must not raise


def test_the_room_listener_is_taken_off_again_on_shutdown() -> None:
    """A worker process runs many jobs; each must leave the room as it found it."""
    room = FakeRoom()
    capture = _capture(room)
    assert room.handlers["data_received"]

    capture.detach()

    assert room.handlers["data_received"] == []


def test_detaching_twice_is_harmless() -> None:
    room = FakeRoom()
    capture = _capture(room)
    capture.detach()
    capture.detach()
