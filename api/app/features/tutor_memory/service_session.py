"""What a dashboard assistant session is told before it speaks.

`assistant.service.start_session` calls this when a session starts, so this
module's shape is "given a session, return the four things the worker needs"
rather than a use case of its own.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import RenderFailed, TutorPromptRenderer
from app.features.tutor_memory import service_brief
from app.features.tutor_memory.renderer import LABELS
from app.features.tutor_memory.tools_catalog import CATALOG

log = get_logger(__name__)

DASHBOARD = "dashboard"

# Said before the instructions are read, so it must not depend on them. The
# returning form is used only when there is a conversation to return to.
GREETING_FIRST_TIME = "Hello. What would you like to work on today?"
GREETING_RETURNING = "Good to see you again. Shall we pick up where we left off?"


async def render_dashboard_session(
    session: AsyncSession,
    *,
    session_type: str,
    user_id: uuid.UUID,
    now: datetime,
    renderer: TutorPromptRenderer | None = None,
) -> dict[str, Any] | None:
    """The tutor's instructions, greeting and tools — or `None` for any other kind.

    Returning `None` rather than raising is what lets this stay one call:
    `assistant` asks about every session it starts and keeps its own
    placeholder text for the three kinds this slice has nothing to say about.
    """
    if session_type != DASHBOARD:
        return None

    brief = await service_brief.compose(session, user_id=user_id, now=now)
    try:
        instructions = (renderer or _renderer()).render(brief=brief, labels=LABELS)
    except RenderFailed as exc:
        # Not fatal: a dashboard session with the placeholder instructions is a
        # worse conversation, and one that refuses to start is no conversation.
        log.warning("tutor prompt not rendered", user_id=str(user_id), error=str(exc))
        return None

    return {
        "instructions": instructions,
        "greeting": GREETING_RETURNING if brief.get("last_conversation") else GREETING_FIRST_TIME,
        "tools": [dict(tool) for tool in CATALOG],
        "extras": {},
    }


def _renderer() -> TutorPromptRenderer:
    """The default renderer, imported lazily so a test can pass its own instead."""
    from app.features.tutor_memory.renderer import build_renderer

    return build_renderer()
