"""
BaseComputerTool — shared LiveKit screenshot capture, pointer overlay, and tool wiring.

AnthropicComputerTool inherits from this class.
Subclasses only override `_analyse_screenshot()` to plug in their vision backend.

Frontend (browser) — where the screenshot is taken:
  • RPC handler: frontend/src/packages/livekit-ui-guidance/registerScreenshotRpc.ts
  • Registration at connect time: e.g. LivekitHelpService.tsx calls
    registerScreenshotRpc(localParticipant) when UI guidance is enabled.

Screenshot transport (v2 — chunked data channel):
  1. Worker generates a unique screenshot_id, calls perform_rpc with {"screenshotId": ...}.
  2. Browser captures DOM → publishes each chunk as type="sc_chunk", field "id" = screenshot_id.
  3. Worker reassembles chunks in order.
  4. RPC return value is metadata only (sizes, chunk count); image bytes use the data channel
     so we stay under LiveKit's small RPC payload limit.

Coordinate contract:
  The LLM sees an image of size captureWidth × captureHeight and returns coordinates
  in THAT space.  We map to viewport CSS pixels:
      x_vp = x_raw * viewportWidth  / captureWidth
      y_vp = y_raw * viewportHeight / captureHeight
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from livekit.agents import JobContext, RunContext
from livekit.agents.llm import function_tool

from livekit_assistant_worker.ui_guidance.navigation import NavigationModeState
from livekit_assistant_worker.ui_guidance.contracts import (
    POINTER_MESSAGE_TYPE,
    RPC_METHOD_PERFORM_CLICK,
    RPC_METHOD_SCREENSHOT_CHUNKED,
    RPC_METHOD_SCROLL,
    TOOL_RUNNING_MESSAGE_TYPE,
    UI_GUIDANCE_SCHEMA_VERSION,
)
from voice_infra.tool_log import agent_tool_log, log_llm_tool_use_shape
from voice_infra.tool_progress import filler_kwargs, filler_line
import logging

main_logger = logging.getLogger(__name__)

# ── Module-level constants ────────────────────────────────────────────────────

DISPLAY_W = int(os.getenv("UI_GUIDANCE_DISPLAY_WIDTH", "1280"))
DISPLAY_H = int(os.getenv("UI_GUIDANCE_DISPLAY_HEIGHT", "720"))
MAX_PER_MINUTE = int(os.getenv("UI_GUIDANCE_MAX_CALLS_PER_MINUTE", "30"))
_WINDOW_SEC = 60.0

_rate_buckets: dict[str, list[float]] = defaultdict(list)

COMPUTER_TOOL_SCHEMA = {
    "name": "computer",
    "description": (
        "Interact with the application UI visible on screen. "
        "Use action=screenshot to capture the current view. "
        "Use action=show_pointer with coordinate=[x, y] to show a highlight overlay — only when "
        "the user is in guided (highlight) mode; they click themselves. "
        "In hands-off mode ('Navigate for me' on screen), use action=perform_click for each "
        "navigation step instead of show_pointer — do not ask the user to click. "
        "perform_click synthesizes a browser click at the coordinate (viewport pixels mapped from the "
        "last screenshot). Never use perform_click for destructive or submit actions. "
        "Use action=scroll to scroll the page or nested panels when the target is off-screen; "
        "then take another screenshot."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "show_pointer", "perform_click", "scroll"],
                "description": (
                    "screenshot = capture the page as an image for analysis. "
                    "show_pointer = highlight overlay at coordinate (guided mode). "
                    "perform_click = synthetic click at coordinate (automate mode only). "
                    "scroll = scroll the viewport or scrollable region (up/down/left/right)."
                ),
            },
            "coordinate": {
                "type": "array",
                "items": {"type": "number"},
                "description": (
                    "[x, y] pixel position in the screenshot image (same space as the last "
                    "screenshot). Required for show_pointer and perform_click."
                ),
            },
            "label": {
                "type": "string",
                "description": (
                    "Short name of the on-screen element, as the FAQ names it. "
                    "Optional metadata for logs."
                ),
            },
            "direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
                "description": "Required for action=scroll. Which direction to scroll.",
            },
            "amount_px": {
                "type": "number",
                "description": (
                    "Optional for action=scroll. Distance in CSS pixels (roughly 400 if omitted)."
                ),
            },
        },
        "required": ["action"],
    },
}


# ── Base class ────────────────────────────────────────────────────────────────

class BaseComputerTool(ABC):
    """
    Shared infrastructure for LiveKit screenshot capture, pointer overlay,
    rate limiting, loading indicator, and tool wiring.

    Subclasses implement `_analyse_screenshot` to plug in a vision backend.
    """

    # Subclasses can override for log prefixes (e.g. "ANTHROPIC", "OPENAI").
    _LOG_PREFIX: str = "COMPUTER_TOOL"

    def __init__(self, ctx: JobContext, worker_type: str, navigation: NavigationModeState | None = None) -> None:
        self._ctx = ctx
        self._worker_type = worker_type
        self._navigation = navigation or NavigationModeState()

        self._last_vw: int = DISPLAY_W
        self._last_vh: int = DISPLAY_H
        self._last_cw: int = DISPLAY_W
        self._last_ch: int = DISPLAY_H

        self._pending: dict[str, dict[str, Any]] = {}
        # One browser RPC at a time: parallel screenshot + perform_click (or two clicks)
        # starves the LiveKit RPC layer and yields Response timeout / wrong ordering.
        self._browser_rpc_lock = asyncio.Lock()

        ctx.room.on("data_received", self._on_data_received)

    def _get_navigation_mode(self) -> str:
        return self._navigation.mode

    # ── Rate limiting ─────────────────────────────────────────────────────────

    def _is_rate_limited(self) -> bool:
        now = time.monotonic()
        bucket = _rate_buckets[self._ctx.room.name]
        bucket[:] = [t for t in bucket if now - t < _WINDOW_SEC]
        if len(bucket) >= MAX_PER_MINUTE:
            return True
        bucket.append(now)
        return False

    # ── Incoming data-channel handler (sc_chunk messages) ────────────────────

    def _on_data_received(self, data_packet) -> None:
        try:
            packet_bytes = getattr(data_packet, "data", data_packet)
            if not isinstance(packet_bytes, (bytes, bytearray)):
                return
            msg = json.loads(packet_bytes)
            if msg.get("type") != "sc_chunk":
                return

            screenshot_id = msg["id"]
            entry = self._pending.get(screenshot_id)
            if entry is None:
                return

            entry["chunks"][int(msg["i"])] = msg["d"]
            entry["received"] += 1

            if entry["total"] is not None and entry["received"] >= entry["total"]:
                entry["event"].set()
        except Exception:
            pass

    # ── Screenshot RPC (shared chunk protocol) ────────────────────────────────

    async def _capture_screenshot(self) -> tuple[str, str] | None:
        """
        Ask the user's browser (via LiveKit RPC) to capture the page, reassemble
        base64 chunks.  Returns (base64_jpeg, media_type) or None on failure.
        Also updates self._last_vw/vh/cw/ch from the RPC metadata.
        """
        room = self._ctx.room
        user_browser_identity = next(
            (p.identity for p in room.remote_participants.values()), None
        )
        if not user_browser_identity:
            agent_tool_log(f"{self._LOG_PREFIX} screenshot_fail reason=no_remote_participant")
            return None

        screenshot_id = uuid.uuid4().hex[:12]
        entry: dict[str, Any] = {
            "chunks": {},
            "total": None,
            "received": 0,
            "event": asyncio.Event(),
        }
        self._pending[screenshot_id] = entry

        try:
            async with self._browser_rpc_lock:
                resp = await room.local_participant.perform_rpc(
                    destination_identity=user_browser_identity,
                    method=RPC_METHOD_SCREENSHOT_CHUNKED,
                    payload=json.dumps({"screenshotId": screenshot_id}),
                    response_timeout=60.0,
                )
                meta = json.loads(resp)

                self._last_vw = int(meta["viewportWidth"])
                self._last_vh = int(meta["viewportHeight"])
                self._last_cw = int(meta["captureWidth"])
                self._last_ch = int(meta["captureHeight"])
                media_type: str = meta.get("mediaType", "image/jpeg")
                total: int = int(meta["totalChunks"])

                entry["total"] = total
                if entry["received"] >= total:
                    entry["event"].set()

                await asyncio.wait_for(entry["event"].wait(), timeout=30.0)

                jpeg_b64 = "".join(entry["chunks"][i] for i in range(total))
                agent_tool_log(
                    f"{self._LOG_PREFIX} screenshot_ok "
                    f"vw={self._last_vw} vh={self._last_vh} "
                    f"cw={self._last_cw} ch={self._last_ch} "
                    f"media={media_type} b64_chars={len(jpeg_b64)} chunks={total}"
                )
                return jpeg_b64, media_type

        except asyncio.TimeoutError:
            received = entry["received"]
            total_str = str(entry.get("total", "?"))
            agent_tool_log(
                f"{self._LOG_PREFIX} screenshot_timeout screenshot_id={screenshot_id} "
                f"received={received}/{total_str}"
            )
            main_logger.warning(f"[{self._LOG_PREFIX}] Screenshot chunk timeout: {received}/{total_str} chunks")
            return None
        except Exception as e:
            agent_tool_log(f"{self._LOG_PREFIX} screenshot_fail error={e!r}")
            main_logger.warning(f"[{self._LOG_PREFIX}] RPC screenshot failed: {e}")
            return None
        finally:
            self._pending.pop(screenshot_id, None)

    # ── Abstract: vision backend ──────────────────────────────────────────────

    @abstractmethod
    async def _analyse_screenshot(self, jpeg_b64: str, media_type: str) -> str:
        """
        Process the captured screenshot and return a tool-result string
        (JSON-encoded list of content blocks).

        Subclass contract:
          • Anthropic: wraps the image as a native image block for Claude.
          • OpenAI: runs the Responses API computer-use loop, returns text analysis.
        """

    # ── Loading indicator ─────────────────────────────────────────────────────

    async def _set_tool_running(self, active: bool) -> None:
        try:
            await self._ctx.room.local_participant.publish_data(
                json.dumps({"type": TOOL_RUNNING_MESSAGE_TYPE, "active": active}).encode(),
                reliable=True,
            )
        except Exception:
            pass

    # ── Pointer overlay ───────────────────────────────────────────────────────

    async def _show_pointer(self, coordinate: list, label: str) -> str:
        x_capture_px, y_capture_px = float(coordinate[0]), float(coordinate[1])
        x_vp = max(0, min(int(round(x_capture_px * self._last_vw / self._last_cw)), self._last_vw))
        y_vp = max(0, min(int(round(y_capture_px * self._last_vh / self._last_ch)), self._last_vh))

        payload = {
            "type": POINTER_MESSAGE_TYPE,
            "schemaVersion": UI_GUIDANCE_SCHEMA_VERSION,
            "x": x_vp,
            "y": y_vp,
            "text": label,
        }
        try:
            await self._ctx.room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"), reliable=True
            )
            agent_tool_log(
                f"{self._LOG_PREFIX} pointer_sent "
                f"capture_xy=({x_capture_px:.0f},{y_capture_px:.0f}) "
                f"capture_size=({self._last_cw},{self._last_ch}) "
                f"viewport_size=({self._last_vw},{self._last_vh}) "
                f"viewport_xy=({x_vp},{y_vp})"
            )
        except Exception as e:
            agent_tool_log(f"{self._LOG_PREFIX} publish_fail error={e!r}")
            main_logger.warning(f"[{self._LOG_PREFIX}] publish_data failed: {e}")
            return json.dumps([{"type": "text", "text": "Could not show pointer; describe the steps verbally."}])

        return json.dumps([{
            "type": "text",
            "text": f"Pointer placed at '{label}' ({x_vp}, {y_vp}).",
        }])

    async def _perform_click(self, coordinate: list, label: str) -> str:
        if self._get_navigation_mode() != "automate":
            return json.dumps([{
                "type": "text",
                "text": (
                    "perform_click is only available after the user taps "
                    "'Navigate for me' on screen. Use show_pointer and wait for them to say "
                    "next, or ask them to choose hands-off navigation."
                ),
            }])

        x_capture_px, y_capture_px = float(coordinate[0]), float(coordinate[1])
        x_vp = max(0, min(int(round(x_capture_px * self._last_vw / self._last_cw)), self._last_vw))
        y_vp = max(0, min(int(round(y_capture_px * self._last_vh / self._last_ch)), self._last_vh))

        room = self._ctx.room
        user_browser_identity = next(
            (p.identity for p in room.remote_participants.values()), None
        )
        if not user_browser_identity:
            agent_tool_log(f"{self._LOG_PREFIX} perform_click_fail reason=no_remote_participant")
            return json.dumps([{"type": "text", "text": "Could not click; no browser participant."}])

        await self._set_tool_running(True)
        try:
            async with self._browser_rpc_lock:
                resp = await room.local_participant.perform_rpc(
                    destination_identity=user_browser_identity,
                    method=RPC_METHOD_PERFORM_CLICK,
                    payload=json.dumps({"x": x_vp, "y": y_vp}),
                    response_timeout=30.0,
                )
                meta = json.loads(resp)
                ok = bool(meta.get("ok"))
                if ok:
                    path = meta.get("pathname", "")
                    agent_tool_log(
                        f"{self._LOG_PREFIX} perform_click_ok viewport_xy=({x_vp},{y_vp}) "
                        f"label={label!r} pathname={path!r}"
                    )
                    extra = f" Path is now {path}." if path else ""
                    return json.dumps([{
                        "type": "text",
                        "text": f"Clicked '{label or 'target'}' at ({x_vp}, {y_vp}).{extra}",
                    }])
                err = meta.get("error", "unknown")
                agent_tool_log(f"{self._LOG_PREFIX} perform_click_fail error={err!r}")
                return json.dumps([{
                    "type": "text",
                    "text": f"Click failed ({err}). Describe the next step verbally or try show_pointer.",
                }])
        except Exception as e:
            agent_tool_log(f"{self._LOG_PREFIX} perform_click_rpc_error error={e!r}")
            main_logger.warning(f"[{self._LOG_PREFIX}] perform_click RPC failed: {e}")
            return json.dumps([{
                "type": "text",
                "text": "Could not perform the click; continue with verbal guidance.",
            }])
        finally:
            await self._set_tool_running(False)

    async def _perform_scroll(self, raw_arguments: dict) -> str:
        direction = str(raw_arguments.get("direction", "")).lower().strip()
        if direction not in ("up", "down", "left", "right"):
            return json.dumps([{
                "type": "text",
                "text": "scroll requires direction: up, down, left, or right.",
            }])

        amount_raw = raw_arguments.get("amount_px", raw_arguments.get("amountPx"))
        payload: dict[str, Any] = {"direction": direction}
        if amount_raw is not None:
            try:
                payload["amount_px"] = float(amount_raw)
            except (TypeError, ValueError):
                pass

        room = self._ctx.room
        user_browser_identity = next(
            (p.identity for p in room.remote_participants.values()), None
        )
        if not user_browser_identity:
            agent_tool_log(f"{self._LOG_PREFIX} scroll_fail reason=no_remote_participant")
            return json.dumps([{"type": "text", "text": "Could not scroll; no browser participant."}])

        try:
            async with self._browser_rpc_lock:
                resp = await room.local_participant.perform_rpc(
                    destination_identity=user_browser_identity,
                    method=RPC_METHOD_SCROLL,
                    payload=json.dumps(payload),
                    response_timeout=15.0,
                )
                meta = json.loads(resp)
                ok = bool(meta.get("ok"))
                if ok:
                    moved = meta.get("moved")
                    sx = meta.get("scroll_x")
                    sy = meta.get("scroll_y")
                    agent_tool_log(
                        f"{self._LOG_PREFIX} scroll_ok direction={direction!r} "
                        f"moved={moved!r} scroll=({sx},{sy})"
                    )
                    hint = (
                        " Take another screenshot to see if the target is visible."
                        if moved
                        else " Nothing appeared to scroll; the page may use a different scroll container — say so and suggest the user scroll manually."
                    )
                    return json.dumps([{
                        "type": "text",
                        "text": f"Scrolled {direction}.{hint}",
                    }])
                err = meta.get("error", "unknown")
                agent_tool_log(f"{self._LOG_PREFIX} scroll_fail error={err!r}")
                return json.dumps([{
                    "type": "text",
                    "text": f"Scroll failed ({err}). Ask the user to scroll manually if needed.",
                }])
        except Exception as e:
            agent_tool_log(f"{self._LOG_PREFIX} scroll_rpc_error error={e!r}")
            main_logger.warning(f"[{self._LOG_PREFIX}] scroll RPC failed: {e}")
            return json.dumps([{
                "type": "text",
                "text": "Could not scroll the page; ask the user to scroll manually.",
            }])

    # ── Tool entry point ──────────────────────────────────────────────────────

    async def handle(self, raw_arguments: dict, ctx: RunContext) -> str:
        action = raw_arguments.get("action", "screenshot")
        coordinate = raw_arguments.get("coordinate")
        label = str(raw_arguments.get("label", "")).strip()

        agent_tool_log(
            f"{self._LOG_PREFIX} action={action!r} coordinate={coordinate} "
            f"direction={raw_arguments.get('direction')!r} worker={self._worker_type!r}"
        )

        if self._is_rate_limited():
            agent_tool_log(f"{self._LOG_PREFIX} rate_limited")
            return json.dumps([{"type": "text", "text": "Rate limit reached; describe the steps verbally."}])

        if action == "screenshot":
            await ctx.update("I'm looking at your screen now.")
            await self._set_tool_running(True)
            try:
                async with ctx.with_filler(filler_line, **filler_kwargs()):
                    result = await self._capture_screenshot()
                    if result is None:
                        return json.dumps(
                            [
                                {
                                    "type": "text",
                                    "text": "Could not capture the screen; describe steps verbally.",
                                }
                            ]
                        )
                    await ctx.update(
                        "Got your screen. Working out the best way to guide you."
                    )
                    jpeg_b64, media_type = result
                    return await self._analyse_screenshot(jpeg_b64, media_type)
            finally:
                await self._set_tool_running(False)

        if action == "show_pointer" and coordinate:
            await ctx.update("I'll highlight that on your screen.")
            async with ctx.with_filler(filler_line, **filler_kwargs()):
                return await self._show_pointer(coordinate, label)

        if action == "perform_click" and coordinate:
            await ctx.update("I'll click that for you.")
            async with ctx.with_filler(filler_line, **filler_kwargs()):
                return await self._perform_click(coordinate, label)

        if action == "scroll":
            await ctx.update("I'll scroll the page.")
            async with ctx.with_filler(filler_line, **filler_kwargs()):
                return await self._perform_scroll(raw_arguments)

        agent_tool_log(f"{self._LOG_PREFIX} unsupported_action action={action!r}")
        return json.dumps([{"type": "text", "text": f"Action '{action}' is not supported in this environment."}])

    # ── Factory ───────────────────────────────────────────────────────────────

    def as_function_tool(self):
        """Returns a @function_tool-decorated callable ready to append to Agent tools."""
        @function_tool(raw_schema=COMPUTER_TOOL_SCHEMA)
        async def computer(raw_arguments: dict, ctx: RunContext) -> str:
            log_llm_tool_use_shape("computer", raw_arguments, run_ctx=ctx)
            return await self.handle(raw_arguments, ctx)

        return computer
