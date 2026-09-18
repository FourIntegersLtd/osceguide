"""Answering the two tools that write something down.

Split from `service_tools.py`, which had grown past the file cap: that module
is the dispatcher and the read-only tools, this one is the two that change
what the tutor will say next time.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory import action_plan, repository
from app.features.tutor_memory.schemas import ToolResult

# How far back to look for a step still open. A plan is agreed at a debrief
# and reported on days later, often after other debriefs; ten covers months of
# practice without scanning a whole history on every call.
MARK_DONE_LOOKBACK = 10


async def mark_done(session: AsyncSession, *, user_id: uuid.UUID, step: str) -> ToolResult:
    """Tick off a step agreed in an earlier debrief.

    `done` was a field the summariser wrote as `False` and nothing ever set
    true, so `open_action_items` never filtered anything and the brief listed
    every step ever agreed, for ever — the tutor kept asking about work
    finished months ago. It degraded rather than failed, which is why it
    lasted.

    The most recent debrief that still has this step open wins. Searching
    back through them rather than only the latest is the point: a doctor
    reports having done something a fortnight after agreeing it, by which
    time there have been other debriefs.
    """
    summaries = await repository.recent_debrief_summaries(session, user_id, limit=MARK_DONE_LOOKBACK)
    for summary in summaries:
        plan = list(summary.action_plan or [])
        updated, matched = action_plan.mark_action_item_done(plan, step)
        if matched is None:
            continue
        await repository.set_action_plan(session, summary.id, updated)
        return ToolResult(result=f"Ticked off: {matched}. Acknowledge it briefly and move on.")
    # Deliberately not guessed at. Ticking off the wrong step is worse than
    # ticking off none: the doctor then gets asked about the thing they did
    # and never about the thing they did not.
    return ToolResult(
        result=(
            "Nothing matching that is still open on their action plans. Do not invent one — "
            "ask which step they mean, or carry on."
        )
    )
