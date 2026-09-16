"""Notes pushed into a running model's context without making it speak.

A worker sometimes needs to tell the persona something mid-interaction --- that
the clock is running out, that the time for one phase is up. The note goes in
as a system message on the agent's chat context, which means the model reads it
before its *next* reply rather than answering it immediately. That one property
is the whole point: a notice must never make the model talk over the person it
is listening to.

It also means a note takes effect one turn late when it lands mid-monologue.
That is the accepted price, not a bug.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["apply_notice"]


async def apply_notice(session: Any, text: str) -> None:
    """Append a system line to the active agent's chat context; never raises."""
    try:
        agent = getattr(session, "current_agent", None)
        if agent is None:
            logger.warning("notice dropped: no active agent")
            return
        chat_ctx = agent.chat_ctx.copy()
        chat_ctx.add_message(role="system", content=text)
        await agent.update_chat_ctx(chat_ctx)
    except Exception as exc:  # noqa: BLE001 — a lost notice must not end the interaction
        logger.warning("notice not applied: %s", exc)
