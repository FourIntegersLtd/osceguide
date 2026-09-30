"""Cloud-slot calls addressed by endpoints; the legacy product tests are the oracle."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import voice_infra.cloud_slot as cloud_slot
from voice_infra import BackendEndpoints

PRACTICE = BackendEndpoints(
    label="practice",
    base_url_env="PRACTICE_URL",
    secret_env="PRACTICE_SECRET",
    secret_header="X-Practice-Secret",
    slot_release_path="/api/worker/livekit-cloud-slot/release",
    slot_extend_path="/api/worker/livekit-cloud-slot/extend",
    slot_payload_key="room_name",
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("PRACTICE_URL", raising=False)
    monkeypatch.delenv("PRACTICE_SECRET", raising=False)


def test_release_posts_payload_and_secret_from_the_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s3cret")
    post = AsyncMock(return_value=200)
    with patch.object(cloud_slot, "post_json", new=post):
        asyncio.run(cloud_slot.release_cloud_slot_async(" room-1 ", PRACTICE))
    args, kwargs = post.await_args
    assert args == ("https://api.test/api/worker/livekit-cloud-slot/release", {"room_name": "room-1"})
    assert kwargs == {"headers": {"X-Practice-Secret": "s3cret"}, "timeout": 5.0}


def test_extend_uses_the_extend_path(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    post = AsyncMock(return_value=200)
    with patch.object(cloud_slot, "post_json", new=post):
        asyncio.run(cloud_slot.extend_cloud_slot_async("room-1", PRACTICE))
    assert post.await_args.args[0].endswith("/extend")
    assert post.await_args.kwargs["headers"] == {}


@pytest.mark.parametrize("room", ["", "   ", None])
def test_blank_room_is_a_no_op(monkeypatch, room) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    post = AsyncMock()
    with patch.object(cloud_slot, "post_json", new=post):
        asyncio.run(cloud_slot.release_cloud_slot_async(room, PRACTICE))
    post.assert_not_awaited()


def test_missing_backend_url_skips_the_call() -> None:
    post = AsyncMock()
    with patch.object(cloud_slot, "post_json", new=post):
        asyncio.run(cloud_slot.release_cloud_slot_async("room-1", PRACTICE))
    post.assert_not_awaited()


def test_post_failure_is_swallowed(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    post = AsyncMock(side_effect=RuntimeError("down"))
    with patch.object(cloud_slot, "post_json", new=post):
        asyncio.run(cloud_slot.release_cloud_slot_async("room-1", PRACTICE))
    post.assert_awaited_once()


def test_lifecycle_extends_now_and_releases_on_shutdown(monkeypatch) -> None:
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    ctx = SimpleNamespace(room=SimpleNamespace(name="room-9"), shutdown_callbacks=[])
    ctx.add_shutdown_callback = ctx.shutdown_callbacks.append
    post = AsyncMock(return_value=200)

    async def run() -> None:
        with patch.object(cloud_slot, "post_json", new=post):
            cloud_slot.register_cloud_slot_lifecycle(ctx, PRACTICE)
            await asyncio.sleep(0)
            assert post.await_args.args[0].endswith("/extend")
            for callback in ctx.shutdown_callbacks:
                await callback()

    asyncio.run(run())
    assert [call.args[0].rsplit("/", 1)[-1] for call in post.await_args_list] == ["extend", "release"]
