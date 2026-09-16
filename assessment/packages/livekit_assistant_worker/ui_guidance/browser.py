"""Talking to the one browser in the room.

Everything the guidance tool does to the page goes through here: the RPCs that
ask the browser to act, and the data-channel messages that tell it what to draw.
Nothing in this module knows what an action means.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class BrowserChannel:
    """The user's browser, as a pair of pipes."""

    def __init__(self, room: Any) -> None:
        self._room = room
        # One browser RPC at a time. Overlapping calls starve the LiveKit RPC
        # layer and come back as response timeouts, or in the wrong order.
        self._lock = asyncio.Lock()

    @property
    def identity(self) -> str | None:
        """The remote participant to address, or None when nobody is connected."""
        return next((p.identity for p in self._room.remote_participants.values()), None)

    @asynccontextmanager
    async def exclusive(self) -> AsyncIterator[None]:
        """Hold the browser for a sequence that must not interleave with another."""
        async with self._lock:
            yield

    async def rpc(self, method: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        """Call the browser and return its parsed response.

        Raises on transport failure so the caller can report the specific action
        that failed; a missing browser raises ``BrowserUnavailable``.
        """
        identity = self.identity
        if identity is None:
            raise BrowserUnavailable(method)
        response = await self._room.local_participant.perform_rpc(
            destination_identity=identity,
            method=method,
            payload=json.dumps(payload),
            response_timeout=timeout,
        )
        parsed = json.loads(response)
        return parsed if isinstance(parsed, dict) else {}

    async def publish(self, payload: dict[str, Any]) -> bool:
        """Send a data-channel message to the room. Never raises."""
        try:
            await self._room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"), reliable=True
            )
            return True
        except Exception as exc:  # noqa: BLE001 — a dropped overlay must not end the turn
            logger.warning("[ui_guidance] publish failed type=%s: %s", payload.get("type"), exc)
            return False


class BrowserUnavailable(RuntimeError):
    """No browser is connected to the room."""

    def __init__(self, method: str) -> None:
        super().__init__(f"no browser participant for {method}")
