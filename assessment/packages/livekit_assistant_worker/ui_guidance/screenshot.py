"""Getting a picture of the page out of the browser.

The image is too large for an RPC response, so the RPC only triggers the capture
and reports how many pieces to expect; the pieces themselves arrive as
data-channel messages. This module owns that two-lane protocol and the room
listener it needs, including taking the listener back off again.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from voice_infra.data_packets import json_packet
from voice_infra.tool_log import agent_tool_log

from .browser import BrowserChannel, BrowserUnavailable
from .contracts import DATA_TYPE_SCREENSHOT_CHUNK, RPC_METHOD_SCREENSHOT_CHUNKED
from .geometry import Viewport

logger = logging.getLogger(__name__)

RPC_TIMEOUT_SECONDS = 60.0
CHUNK_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class Screenshot:
    image_b64: str
    media_type: str
    viewport: Viewport


@dataclass
class _Pending:
    """Chunks arriving for one capture, which may start before the RPC returns."""

    chunks: dict[int, str] = field(default_factory=dict)
    expected: int | None = None
    complete: asyncio.Event = field(default_factory=asyncio.Event)

    def add(self, index: int, fragment: str) -> None:
        self.chunks[index] = fragment
        self._settle()

    def expect(self, total: int) -> None:
        self.expected = total
        self._settle()

    def _settle(self) -> None:
        if self.expected is not None and len(self.chunks) >= self.expected:
            self.complete.set()

    def assemble(self) -> str:
        return "".join(self.chunks[i] for i in range(self.expected or 0))


class ScreenshotCapture:
    """Captures the page, reassembling the chunked image the browser sends back."""

    def __init__(
        self,
        room: Any,
        browser: BrowserChannel,
        *,
        rpc_timeout: float = RPC_TIMEOUT_SECONDS,
        chunk_timeout: float = CHUNK_TIMEOUT_SECONDS,
    ) -> None:
        self._room = room
        self._browser = browser
        self._rpc_timeout = rpc_timeout
        self._chunk_timeout = chunk_timeout
        self._pending: dict[str, _Pending] = {}
        self._attached = False
        self.viewport = Viewport()

    # -- listener lifecycle ------------------------------------------------------

    def attach(self) -> None:
        if self._attached:
            return
        self._room.on("data_received", self._on_data_received)
        self._attached = True

    def detach(self) -> None:
        """Stop listening. Called on shutdown so a finished job leaves no handler behind."""
        if not self._attached:
            return
        self._room.off("data_received", self._on_data_received)
        self._attached = False

    def _on_data_received(self, data_packet: Any) -> None:
        message = json_packet(data_packet)
        if not message or message.get("type") != DATA_TYPE_SCREENSHOT_CHUNK:
            return
        pending = self._pending.get(str(message.get("id")))
        if pending is None:
            return
        try:
            pending.add(int(message["i"]), str(message["d"]))
        except (KeyError, TypeError, ValueError):
            # A malformed chunk would otherwise be indistinguishable from a missing
            # one, and surface thirty seconds later as a timeout.
            logger.warning("[ui_guidance] discarding malformed screenshot chunk")

    # -- capture -----------------------------------------------------------------

    async def capture(self) -> Screenshot | None:
        """The page as the user currently sees it, or None if it could not be taken."""
        screenshot_id = uuid.uuid4().hex[:12]
        pending = _Pending()
        self._pending[screenshot_id] = pending
        try:
            async with self._browser.exclusive():
                meta = await self._browser.rpc(
                    RPC_METHOD_SCREENSHOT_CHUNKED,
                    {"screenshotId": screenshot_id},
                    timeout=self._rpc_timeout,
                )
                self.viewport = Viewport.from_metadata(meta)
                media_type = str(meta.get("mediaType", "image/jpeg"))
                pending.expect(int(meta["totalChunks"]))
                await asyncio.wait_for(pending.complete.wait(), timeout=self._chunk_timeout)

            image_b64 = pending.assemble()
            agent_tool_log(
                f"ui_guidance screenshot_ok chunks={pending.expected} "
                f"b64_chars={len(image_b64)} media={media_type} "
                f"viewport=({self.viewport.viewport_width},{self.viewport.viewport_height}) "
                f"capture=({self.viewport.capture_width},{self.viewport.capture_height})"
            )
            return Screenshot(image_b64=image_b64, media_type=media_type, viewport=self.viewport)

        except BrowserUnavailable:
            agent_tool_log("ui_guidance screenshot_fail reason=no_browser")
            return None
        except asyncio.TimeoutError:
            agent_tool_log(
                f"ui_guidance screenshot_timeout received={len(pending.chunks)}/{pending.expected}"
            )
            logger.warning(
                "[ui_guidance] screenshot chunks timed out: %s/%s", len(pending.chunks), pending.expected
            )
            return None
        except Exception as exc:  # noqa: BLE001 — guidance degrades to speech, the session continues
            agent_tool_log(f"ui_guidance screenshot_fail error={exc!r}")
            logger.warning("[ui_guidance] screenshot failed: %s", exc)
            return None
        finally:
            self._pending.pop(screenshot_id, None)
