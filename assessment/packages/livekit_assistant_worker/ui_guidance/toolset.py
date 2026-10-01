"""The ``computer`` tool: one action table, and the policy that surrounds each action.

The pieces it wires together each hold one concern — ``browser`` the transport,
``screenshot`` the capture protocol, ``actions`` the things that can be done to
the page, ``progress`` what the user hears and sees meanwhile. This module is
where a call arrives, is checked, and is sent to one of them.
"""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import JobContext, RunContext
from livekit.agents.llm import ToolFlag, function_tool

from voice_infra.tool_log import agent_tool_log, log_llm_tool_use_shape

from . import messages
from .actions import GuidanceActions, publish_pointer
from .browser import BrowserChannel
from .contracts import PROGRESS_STEP_READING
from .navigation import NavigationModeState
from .pointer_tags import PointerTag
from .progress import GuidanceProgress, announce, filler, policy_for
from .rate_limit import RateLimit
from .schema import COMPUTER_TOOL_SCHEMA
from .screenshot import ScreenshotCapture
from .vision import as_image_block, as_text

logger = logging.getLogger(__name__)

ACTIONS = ("screenshot", "show_pointer", "perform_click", "scroll")
NEEDS_COORDINATE = ("show_pointer", "perform_click")


class ComputerToolset:
    """One guidance session's view of the user's browser."""

    def __init__(self, ctx: JobContext, worker_type: str, navigation: NavigationModeState | None = None) -> None:
        self._worker_type = worker_type
        self._navigation = navigation or NavigationModeState()
        self._rate = RateLimit()

        self.browser = BrowserChannel(ctx.room)
        self.capture = ScreenshotCapture(ctx.room, self.browser)
        self.progress = GuidanceProgress(self.browser)
        self.actions = GuidanceActions(self.browser, self._navigation, lambda: self.capture.viewport)

        self.capture.attach()
        ctx.add_shutdown_callback(self._shutdown)

    async def _shutdown(self) -> None:
        self.capture.detach()

    # -- inline pointer tags -------------------------------------------------------

    async def point_at(self, tag: PointerTag) -> None:
        """Place the highlight a ``[POINT:…]`` tag in the model's reply asked for."""
        await publish_pointer(self.browser, self.capture.viewport, tag.x, tag.y, tag.label)

    # -- tool ----------------------------------------------------------------------

    async def handle(self, raw_arguments: dict, ctx: RunContext) -> str:
        """Check one call to the computer tool, then run the action it asked for."""
        action = str(raw_arguments.get("action") or "screenshot")
        coordinate = _coordinate(raw_arguments.get("coordinate"))
        label = str(raw_arguments.get("label") or "").strip()

        agent_tool_log(
            f"ui_guidance action={action!r} coordinate={coordinate} "
            f"direction={raw_arguments.get('direction')!r} worker={self._worker_type!r}"
        )

        if action not in ACTIONS:
            agent_tool_log(f"ui_guidance unsupported_action action={action!r}")
            return as_text(messages.UNSUPPORTED_ACTION.format(action=action))
        if action in NEEDS_COORDINATE and coordinate is None:
            agent_tool_log(f"ui_guidance missing_coordinate action={action!r}")
            return as_text(messages.COORDINATE_REQUIRED)
        if not self._rate.take():
            agent_tool_log("ui_guidance rate_limited")
            return as_text(messages.RATE_LIMITED)

        policy = policy_for(action)
        if policy.step:
            await self.progress.enter(policy.step, label=label or None)
        await announce(ctx, policy)

        async with filler(ctx, policy):
            if action == "screenshot":
                return await self._screenshot()
            if action == "show_pointer":
                return await self.actions.show_pointer(coordinate, label)
            if action == "perform_click":
                # A synthetic click is a write: it must finish rather than be
                # cancelled halfway by the user saying "stop".
                ctx.disallow_interruptions()
                return await self.actions.perform_click(coordinate, label)
            return await self.actions.scroll(
                raw_arguments.get("direction"),
                raw_arguments.get("amount_px", raw_arguments.get("amountPx")),
            )

    async def _screenshot(self) -> str:
        """Capture the user's screen and return the image to the model, or a failure message."""
        shot = await self.capture.capture()
        if shot is None:
            await self.progress.done()
            return as_text(messages.SCREENSHOT_FAILED)
        # The image goes back as the tool result, so the model reads it on its next
        # turn. The panel has to stay up across that turn; only the agent speaking
        # clears it.
        await self.progress.enter(PROGRESS_STEP_READING)
        return as_image_block(shot.image_b64, shot.media_type)

    def as_function_tool(self):
        """The decorated callable to hand to the Agent."""

        @function_tool(
            raw_schema=COMPUTER_TOOL_SCHEMA,
            # Screen capture is read-only, so the user can say "stop" and have it
            # end; the framework exposes cancel_task once any tool is cancellable.
            flags=ToolFlag.CANCELLABLE,
            # A model that has not heard back from a running screenshot tends to
            # ask for another. Serialising them only doubles the wait.
            on_duplicate="reject",
        )
        async def computer(raw_arguments: dict, ctx: RunContext) -> str:
            """The tool the model calls to look at the screen, point, click or scroll."""
            log_llm_tool_use_shape("computer", raw_arguments, run_ctx=ctx)
            return await self.handle(raw_arguments, ctx)

        return computer


def _coordinate(raw: Any) -> list[float] | None:
    """The model's [x, y], or None when it did not send a usable pair."""
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return None
    try:
        return [float(raw[0]), float(raw[1])]
    except (TypeError, ValueError):
        return None


def build_computer_toolset(
    ctx: JobContext, worker_type: str, navigation: NavigationModeState | None = None
) -> ComputerToolset:
    return ComputerToolset(ctx, worker_type, navigation)
