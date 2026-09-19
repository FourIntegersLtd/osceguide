"""A room nobody has joined yet is not a failure.

Found in production on the first real exam day run. A circuit dispatches its
patient on the server's clock, so when the reading phase ends the candidate's
browser may not have opened the room. LiveKit answered `not_found`, the
scheduled transition errored, and the circuit sat overdue for ever, because
every retry hit the same empty room.
"""

from __future__ import annotations

import pytest

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
