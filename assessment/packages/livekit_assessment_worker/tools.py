"""Function tools an interaction profile may name, built from its rendered tool context.

The profile lists tool names; this module owns their implementations. A tool
only ever works with the transcript, the room and the clock, never with what
the transcript was about.

The one tool is ``check_time``: the debrief tutor's session clock, which the
backend sends as a pacing plan under ``tool_context["pacing"]``. The plan also
drives the timed notes, so the clock is built whether or not the tool is named,
and the adapter starts it when the session opens.

A profile that names a tool this worker does not implement, or names
``check_time`` without a plan, is a configuration error and says so, rather
than starting a session whose model has been promised a tool that will never
answer.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from voice_infra.pacing import InteractionClock, PacingPlan, build_check_time_tool

logger = logging.getLogger(__name__)

# The tool_context key the backend puts the pacing plan under.
PACING_KEY = "pacing"

ToolBuilder = Callable[[Any, dict[str, Any], InteractionClock | None], Any]


class UnknownToolError(ValueError):
    """The profile named a tool this worker does not implement, or one it cannot build from the context sent."""


def session_clock(tool_context: dict[str, Any]) -> InteractionClock | None:
    """The clock the rendered tool context carries, unstarted; None when the backend sent no plan."""
    raw_plan = tool_context.get(PACING_KEY)
    return None if raw_plan is None else InteractionClock(PacingPlan.model_validate(raw_plan))


def _build_check_time(ctx: Any, tool_context: dict[str, Any], clock: InteractionClock | None) -> Any:  # noqa: ARG001 — the registry's shape
    """The silent time tool; refused when there is no clock for it to read."""
    if clock is None:
        raise UnknownToolError(f"check_time needs a pacing plan under tool_context[{PACING_KEY!r}]")
    return build_check_time_tool(clock)


TOOL_BUILDERS: dict[str, ToolBuilder] = {"check_time": _build_check_time}


def build_tools(
    ctx: Any, names: tuple[str, ...], tool_context: dict[str, Any], clock: InteractionClock | None
) -> list:
    """The tools a profile names, in order; an unknown name is a configuration error."""
    unknown = [name for name in names if name not in TOOL_BUILDERS]
    if unknown:
        raise UnknownToolError(f"profile names unknown tools {unknown}; available: {sorted(TOOL_BUILDERS)}")
    return [TOOL_BUILDERS[name](ctx, tool_context, clock) for name in names]
