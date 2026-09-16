"""Agent tool: how far through the interaction we are, answered silently.

Unlike the navigation tool, this one says nothing to the person on the other
end --- no ``run_ctx.update`` filler line. A time check that announces itself
tells them the model is watching the clock, which is exactly what the pacing
rules forbid it to do.
"""

from __future__ import annotations

from livekit.agents import RunContext
from livekit.agents.llm import function_tool

from livekit_assistant_worker.pacing import ConsultationClock


def build_check_time_tool(clock: ConsultationClock):
    async def _check_time_impl(run_ctx: RunContext) -> str:  # noqa: ARG001 — the tool takes no arguments
        return clock.status_text()

    return function_tool(
        _check_time_impl,
        name="check_time",
        description=(
            "How far through this interaction you are and which part you should be in. "
            "Silent: the other person hears nothing, and you must never mention the clock, "
            "the time left, or this result out loud. Call it when you are unsure whether to "
            "stay where you are or move on. Use the answer to decide what to leave out, "
            "never to speak faster."
        ),
    )
