"""What the user hears and sees while a guidance action runs.

Two channels, because neither covers the whole wait on its own:

* Speech. ``ctx.update`` hands the model a line to say and releases the tool to
  run in the background; ``ctx.with_filler`` speaks again if the pause drags on.
  Both stop at the moment the tool returns.
* The on-screen panel. It keeps running past the tool, through the model's look
  at the screenshot, until the agent speaks. That turn is the longest silence in
  a guidance turn and speech cannot reach it, because the agent is busy producing
  the very words that would fill it.

Only the screenshot is slow enough to be worth announcing. Announcing a pointer
or a click makes the tool non-blocking, which defers the sentence the user is
actually waiting for to the next idle moment — the narration would cost more
than the wait it describes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from voice_infra.tool_progress import IN_PROGRESS_TEMPLATE, filler_kwargs, filler_line

from .browser import BrowserChannel
from .contracts import (
    DATA_TYPE_GUIDANCE_PROGRESS,
    PROGRESS_STEP_ACTING,
    PROGRESS_STEP_CAPTURING,
    PROGRESS_STEP_DONE,
    PROGRESS_STEP_READING,
    TOOL_RUNNING_MESSAGE_TYPE,
    UI_GUIDANCE_SCHEMA_VERSION,
)

logger = logging.getLogger(__name__)

__all__ = [
    "GuidanceProgress",
    "ProgressPolicy",
    "policy_for",
    "PROGRESS_STEP_ACTING",
    "PROGRESS_STEP_CAPTURING",
    "PROGRESS_STEP_READING",
]


@dataclass(frozen=True)
class ProgressPolicy:
    """How one action narrates itself while it runs."""

    announce: str | None = None
    """Spoken cue, which also releases the tool to run in the background. None keeps it blocking."""

    fill: bool = False
    """Whether to keep speaking if the pause outlasts the cue."""

    step: str | None = None
    """The panel step to show, if any."""


_POLICIES: dict[str, ProgressPolicy] = {
    "screenshot": ProgressPolicy(
        announce="Looking at the user's screen now; still working.",
        fill=True,
        step=PROGRESS_STEP_CAPTURING,
    ),
    "show_pointer": ProgressPolicy(step=PROGRESS_STEP_ACTING),
    "perform_click": ProgressPolicy(step=PROGRESS_STEP_ACTING),
    "scroll": ProgressPolicy(step=PROGRESS_STEP_ACTING),
}

_DEFAULT_POLICY = ProgressPolicy()


def policy_for(action: str) -> ProgressPolicy:
    return _POLICIES.get(action, _DEFAULT_POLICY)


async def announce(ctx: Any, policy: ProgressPolicy) -> None:
    """Speak the cue, if this action has one.

    The template override frames the cue as still running. Without it the model
    is free to voice a mid-action status as though the work had finished.
    """
    if policy.announce:
        await ctx.update(policy.announce, template=IN_PROGRESS_TEMPLATE)


def filler(ctx: Any, policy: ProgressPolicy):
    """The filler context manager for this action, or a no-op for the fast ones."""
    if not policy.fill:
        return _no_filler()
    return ctx.with_filler(filler_line, **filler_kwargs())


class _no_filler:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_exc: Any) -> bool:
        return False


class GuidanceProgress:
    """Publishes the step the guidance turn has reached."""

    def __init__(self, browser: BrowserChannel) -> None:
        self._browser = browser
        self._active: str | None = None

    @property
    def active_step(self) -> str | None:
        return self._active

    async def enter(self, step: str, *, label: str | None = None) -> None:
        self._active = step
        await self._publish(step, label)

    async def done(self) -> None:
        """Clear the panel. Idempotent: the agent may speak several times per turn."""
        if self._active is None:
            return
        self._active = None
        await self._publish(PROGRESS_STEP_DONE, None)

    async def _publish(self, step: str, label: str | None) -> None:
        payload: dict[str, Any] = {
            "type": DATA_TYPE_GUIDANCE_PROGRESS,
            "schemaVersion": UI_GUIDANCE_SCHEMA_VERSION,
            "step": step,
        }
        if label:
            payload["label"] = label
        await self._browser.publish(payload)
        # Kept for a frontend from before the progress panel.
        await self._browser.publish(
            {"type": TOOL_RUNNING_MESSAGE_TYPE, "active": step != PROGRESS_STEP_DONE}
        )
