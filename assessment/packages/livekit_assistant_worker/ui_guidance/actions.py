"""What the guidance tool can do to the page.

Each action converts the model's coordinates, asks the browser to carry it out,
and reports back in the model's own terms. The wording lives in ``messages``, the
plumbing in ``browser``, and the arithmetic in ``geometry``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from voice_infra.tool_log import agent_tool_log

from . import messages
from .browser import BrowserChannel, BrowserUnavailable
from .contracts import POINTER_MESSAGE_TYPE, RPC_METHOD_PERFORM_CLICK, RPC_METHOD_SCROLL, UI_GUIDANCE_SCHEMA_VERSION
from .geometry import Viewport
from .navigation import NavigationModeState
from .vision import as_text

logger = logging.getLogger(__name__)

CLICK_TIMEOUT_SECONDS = 30.0
SCROLL_TIMEOUT_SECONDS = 15.0
SCROLL_DIRECTIONS = ("up", "down", "left", "right")

ViewportSource = Callable[[], Viewport]


async def publish_pointer(
    browser: BrowserChannel, viewport: Viewport, x: float, y: float, label: str
) -> tuple[int, int] | None:
    """Place the highlight. Shared by the tool action and the inline pointer tag."""
    x_vp, y_vp = viewport.to_viewport(x, y)
    payload: dict[str, Any] = {
        "type": POINTER_MESSAGE_TYPE,
        "schemaVersion": UI_GUIDANCE_SCHEMA_VERSION,
        "x": x_vp,
        "y": y_vp,
        "text": label,
    }
    if not await browser.publish(payload):
        return None
    agent_tool_log(
        f"ui_guidance pointer_sent capture=({x:.0f},{y:.0f}) viewport=({x_vp},{y_vp}) label={label!r}"
    )
    return x_vp, y_vp


class GuidanceActions:
    def __init__(
        self,
        browser: BrowserChannel,
        navigation: NavigationModeState,
        viewport: ViewportSource,
    ) -> None:
        self._browser = browser
        self._navigation = navigation
        self._viewport = viewport

    async def show_pointer(self, coordinate: list, label: str) -> str:
        placed = await publish_pointer(self._browser, self._viewport(), coordinate[0], coordinate[1], label)
        if placed is None:
            return as_text(messages.POINTER_FAILED)
        return as_text(messages.POINTER_PLACED.format(label=label or "that", x=placed[0], y=placed[1]))

    async def perform_click(self, coordinate: list, label: str) -> str:
        if self._navigation.mode != "automate":
            return as_text(messages.CLICK_NEEDS_AUTOMATE)

        x_vp, y_vp = self._viewport().to_viewport(coordinate[0], coordinate[1])
        named = label or "that"
        try:
            async with self._browser.exclusive():
                result = await self._browser.rpc(
                    RPC_METHOD_PERFORM_CLICK, {"x": x_vp, "y": y_vp}, timeout=CLICK_TIMEOUT_SECONDS
                )
        except BrowserUnavailable:
            agent_tool_log("ui_guidance click_fail reason=no_browser")
            return as_text(messages.NO_BROWSER)
        except Exception as exc:  # noqa: BLE001 — guidance falls back to speech
            agent_tool_log(f"ui_guidance click_error error={exc!r}")
            logger.warning("[ui_guidance] perform_click failed: %s", exc)
            return as_text(messages.CLICK_FAILED)

        if not result.get("ok"):
            error = result.get("error", "unknown")
            agent_tool_log(f"ui_guidance click_rejected error={error!r}")
            return as_text(messages.CLICK_REJECTED.format(error=error))

        path = result.get("pathname") or ""
        agent_tool_log(f"ui_guidance click_ok viewport=({x_vp},{y_vp}) label={label!r} path={path!r}")
        template = messages.CLICK_OK_NAVIGATED if path else messages.CLICK_OK
        return as_text(template.format(label=named, x=x_vp, y=y_vp, path=path))

    async def scroll(self, direction: str, amount_px: Any = None) -> str:
        direction = str(direction or "").strip().lower()
        if direction not in SCROLL_DIRECTIONS:
            return as_text(messages.SCROLL_NEEDS_DIRECTION)

        payload: dict[str, Any] = {"direction": direction}
        if amount_px is not None:
            try:
                payload["amount_px"] = float(amount_px)
            except (TypeError, ValueError):
                logger.debug("[ui_guidance] ignoring unusable scroll amount %r", amount_px)

        try:
            async with self._browser.exclusive():
                result = await self._browser.rpc(
                    RPC_METHOD_SCROLL, payload, timeout=SCROLL_TIMEOUT_SECONDS
                )
        except BrowserUnavailable:
            agent_tool_log("ui_guidance scroll_fail reason=no_browser")
            return as_text(messages.NO_BROWSER)
        except Exception as exc:  # noqa: BLE001 — guidance falls back to speech
            agent_tool_log(f"ui_guidance scroll_error error={exc!r}")
            logger.warning("[ui_guidance] scroll failed: %s", exc)
            return as_text(messages.SCROLL_FAILED)

        if not result.get("ok"):
            error = result.get("error", "unknown")
            agent_tool_log(f"ui_guidance scroll_rejected error={error!r}")
            return as_text(messages.SCROLL_REJECTED.format(error=error))

        moved = bool(result.get("moved"))
        agent_tool_log(f"ui_guidance scroll_ok direction={direction!r} moved={moved}")
        template = messages.SCROLL_MOVED if moved else messages.SCROLL_STUCK
        return as_text(template.format(direction=direction))
