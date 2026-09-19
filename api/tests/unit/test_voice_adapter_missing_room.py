"""A room nobody has joined yet is not a failure.

Found in production on the first real exam day run. A circuit dispatches its
patient on the server's clock, so when the reading phase ends the candidate's
browser may not have opened the room. LiveKit answered `not_found`, the
scheduled transition errored, and the circuit sat overdue for ever, because
every retry hit the same empty room.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.settings import get_settings
from app.features.voice import adapter
from app.features.voice.adapter import _is_room_missing


@pytest.mark.parametrize(
    "message",
    [
        "ServerError('not_found', 'requested room does not exist')",
        "requested room does not exist",
        "not_found",
    ],
)
def test_a_missing_room_is_recognised(message: str) -> None:
    assert _is_room_missing(Exception(message))


@pytest.mark.parametrize(
    "message",
    [
        "ServerError('unauthenticated', 'invalid API key')",
        "ServerError('permission_denied', 'insufficient permissions')",
        "connection reset by peer",
    ],
)
def test_a_real_failure_is_not_mistaken_for_one(message: str) -> None:
    """Matched on the message because the SDK raises one error type for every
    server condition, so this must not swallow an authentication failure."""
    assert not _is_room_missing(Exception(message))


class _Room:
    """Just enough LiveKit room service to drive `remove_agents`."""

    def __init__(
        self,
        *,
        participants: list[str],
        list_error: Exception | None = None,
        remove_error: Exception | None = None,
    ) -> None:
        self._participants = participants
        self._list_error = list_error
        self._remove_error = remove_error
        self.removed: list[str] = []

    async def list_participants(self, _request: object) -> object:
        if self._list_error is not None:
            raise self._list_error
        return SimpleNamespace(participants=[SimpleNamespace(identity=i) for i in self._participants])

    async def remove_participant(self, request: object) -> None:
        if self._remove_error is not None:
            raise self._remove_error
        self.removed.append(request.identity)


class _Client:
    def __init__(self, room: _Room) -> None:
        self.room = room

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


def _install(monkeypatch: pytest.MonkeyPatch, room: _Room) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "a-livekit-secret-that-is-long-enough")
    get_settings.cache_clear()
    monkeypatch.setattr(
        adapter, "_livekit_api", lambda: SimpleNamespace(LiveKitAPI=lambda *_a, **_k: _Client(room))
    )


MISSING = Exception("ServerError('not_found', 'requested room does not exist')")
BROKEN = Exception("ServerError('unauthenticated', 'invalid API key')")


async def test_a_room_nobody_joined_has_no_agents_to_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    """The production stall: the reading phase ends before the candidate opens
    the room, and every retry of the transition hit this same error."""
    room = _Room(participants=[], list_error=MISSING)
    _install(monkeypatch, room)

    assert await adapter.LiveKitRoomAgents().remove_agents("circuit_abc") == 0
    get_settings.cache_clear()


async def test_a_broken_connection_is_still_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    """Otherwise a bad key would read as an empty room and the sweep would
    silently do nothing for ever."""
    room = _Room(participants=[], list_error=BROKEN)
    _install(monkeypatch, room)

    with pytest.raises(Exception, match="unauthenticated"):
        await adapter.LiveKitRoomAgents().remove_agents("circuit_abc")
    get_settings.cache_clear()


async def test_only_agents_are_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    room = _Room(participants=["agent-patient-1", "candidate-7", "agent-patient-2"])
    _install(monkeypatch, room)

    assert await adapter.LiveKitRoomAgents().remove_agents("circuit_abc") == 2
    assert room.removed == ["agent-patient-1", "agent-patient-2"]
    get_settings.cache_clear()


async def test_a_room_reaped_mid_sweep_is_not_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """`end_circuit` 500'd in production on exactly this path, which left a
    stalled circuit with no way to end it. The listing can succeed and the
    room still be gone by the removal."""
    room = _Room(participants=["agent-patient-1"], remove_error=MISSING)
    _install(monkeypatch, room)

    assert await adapter.LiveKitRoomAgents().remove_agents("circuit_abc") == 0
    get_settings.cache_clear()
