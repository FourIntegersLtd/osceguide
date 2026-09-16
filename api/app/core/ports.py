"""Ports: the interfaces slices use to reach the outside world.

A slice depends on a Protocol here, never on an SDK. Production wires the real
adapter; tests wire a fake from `tests/support/fakes.py`. That is what lets a
service be tested without patching module attributes.

Every port is `runtime_checkable` so a test can assert a fake conforms.
Protocols are added when the first slice needs them; keep this file small.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Protocol, runtime_checkable

from fastapi import Depends


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class EmailDeliveryFailed(Exception):
    """The provider refused or could not deliver the message."""


@runtime_checkable
class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, html: str, reply_to: str | None = None) -> str:
        """Send one email and return the provider's message id. Raises EmailDeliveryFailed."""
        ...


@runtime_checkable
class MembershipProvider(Protocol):
    """Which organisations a user belongs to.

    `identity` needs this to stamp memberships into a token, but sits below
    `tenancy` and may not import it. The provider is a port: `tenancy`
    implements it and `main.py` wires it, so the dependency arrow keeps
    pointing downward and a test can supply a list instead of a database.
    """

    async def for_user(self, session: object, user_id: object) -> list[object]: ...


def get_clock() -> Clock:
    """Overridden in tests with a FakeClock; never patched."""
    return SystemClock()


ClockDep = Annotated[Clock, Depends(get_clock)]
