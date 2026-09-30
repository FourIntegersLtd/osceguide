"""SEC-016: a stream ticket is redeemable once.

A ticket rides in the URL (an `EventSource` cannot set a header), so it can be
lifted from a proxy log or browser history within its sixty-second life. The
first redemption burns its `jti`; a replay is refused. The guard fails open
when Redis is off or unreachable, so a cache outage never drops a live stream —
only the brief replay window reopens.
"""

from __future__ import annotations

import uuid

import pytest

from app.core import streams
from app.core.auth import Principal
from app.core.errors import Unauthenticated
from app.core.settings import Settings


def _settings() -> Settings:
    return Settings(jwt_secret="s" * 40, jwt_issuer="osce-guide")


def _principal() -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        email="watcher@example.com",
        memberships=(),
        active_org_slug=None,
        is_platform_admin=False,
    )


class FakeRedis:
    """Enough Redis to prove single use: `set(nx=True)` succeeds once per key."""

    def __init__(self, *, broken: bool = False) -> None:
        self.keys: set[str] = set()
        self.broken = broken

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None:
        if self.broken:
            raise ConnectionError("redis is down")
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


async def test_a_ticket_redeems_once_and_a_replay_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings()
    redis = FakeRedis()
    monkeypatch.setattr(streams, "get_redis", lambda: redis)
    ticket = streams.issue_stream_ticket(_principal(), settings=settings)

    first = await streams.get_stream_principal(settings=settings, ticket=ticket)
    assert first.email == "watcher@example.com"

    with pytest.raises(Unauthenticated):
        await streams.get_stream_principal(settings=settings, ticket=ticket)


async def test_two_different_tickets_each_redeem(monkeypatch: pytest.MonkeyPatch) -> None:
    """Single use is per ticket, not per person: minting a fresh ticket after
    the first is spent works, so a page can reopen a dropped stream."""
    settings = _settings()
    redis = FakeRedis()
    monkeypatch.setattr(streams, "get_redis", lambda: redis)
    principal = _principal()

    first = streams.issue_stream_ticket(principal, settings=settings)
    second = streams.issue_stream_ticket(principal, settings=settings)
    assert first != second

    await streams.get_stream_principal(settings=settings, ticket=first)
    # A different ticket for the same person is still good.
    await streams.get_stream_principal(settings=settings, ticket=second)


async def test_the_guard_fails_open_when_redis_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """No Redis (local, or a deployment that chose to) means single use is a
    no-op — the ticket still opens its stream rather than being refused."""
    settings = _settings()
    monkeypatch.setattr(streams, "get_redis", lambda: None)
    ticket = streams.issue_stream_ticket(_principal(), settings=settings)

    await streams.get_stream_principal(settings=settings, ticket=ticket)
    # A second redemption is not refused, because nothing remembered the first.
    await streams.get_stream_principal(settings=settings, ticket=ticket)


async def test_the_guard_fails_open_when_redis_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Redis blip mid-redemption must not drop a live stream: the ticket is
    honoured, and only the narrow replay window reopens for the outage."""
    settings = _settings()
    monkeypatch.setattr(streams, "get_redis", lambda: FakeRedis(broken=True))
    ticket = streams.issue_stream_ticket(_principal(), settings=settings)

    watcher = await streams.get_stream_principal(settings=settings, ticket=ticket)
    assert watcher.email == "watcher@example.com"
