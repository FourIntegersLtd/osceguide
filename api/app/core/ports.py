"""Ports: the interfaces slices use to reach the outside world.

A slice depends on a Protocol here, never on an SDK. Production wires the real
adapter; tests wire a fake from `tests/support/`. That is what lets a service
be tested without patching module attributes.

Protocols are added when the first slice needs them; keep this file small.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id."""
        ...
