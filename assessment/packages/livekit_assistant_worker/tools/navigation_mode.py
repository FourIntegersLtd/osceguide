"""Agent tool: publish nav_mode_prompt so the frontend can emphasize mode selection."""

from __future__ import annotations

import json
import uuid

from livekit.agents import JobContext, RunContext
from livekit.agents.llm import function_tool

from livekit_assistant_worker.ui_guidance.contracts import DATA_TYPE_NAV_MODE_PROMPT, UI_GUIDANCE_SCHEMA_VERSION
import logging

main_logger = logging.getLogger(__name__)


def build_offer_navigation_modes_tool(ctx: JobContext):
    async def _offer_navigation_modes_impl(run_ctx: RunContext) -> str:
        # No ctx.update here: publishing a data packet takes milliseconds, and the
        # first update would make the tool non-blocking, deferring the line that
        # tells the user to choose to whenever the session next falls idle.
        payload = {
            "type": DATA_TYPE_NAV_MODE_PROMPT,
            "schemaVersion": UI_GUIDANCE_SCHEMA_VERSION,
            "requestId": uuid.uuid4().hex[:12],
        }
        try:
            await ctx.room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            main_logger.warning(f"offer_navigation_modes publish failed: {e}")
            return "Could not show on-screen navigation options; ask the user verbally how they prefer to proceed."
        return (
            "Navigation choice is shown on the user's screen. Wait until they select an option, "
            "then continue with the appropriate flow: show_pointer for guided mode, or "
            "perform_click only after they chose hands-off navigation."
        )

    return function_tool(
        _offer_navigation_modes_impl,
        name="offer_navigation_modes",
        description=(
            "Show on-screen buttons so the user can choose guided highlights versus hands-off "
            "automated clicks. Call when answering a navigation question that will require "
            "multiple clicks or pages. Do not call for purely verbal FAQs."
        ),
    )
