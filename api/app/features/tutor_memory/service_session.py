"""What a dashboard assistant session is told before it speaks.

`assistant.service.start_session` calls this when a session starts, so this
module's shape is "given a session, return the four things the worker needs"
rather than a use case of its own.
"""

from __future__ import annotations

import random
import uuid
from collections.abc import Mapping
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
# returning forms are used only when there is a conversation to return to. The
# name slot is the first name on the account, or nothing. One line of each set
# is drawn per session: the same opening every time reads as a script.
GREETING_FIRST_TIME = "Hello{name}. What would you like to work on today?"
GREETINGS_RETURNING = (
    "Good to see you again{name}. Shall we pick up where we left off?",
    "Welcome back{name}. Do you want to carry on from last time?",
    "Hello again{name}. Shall we continue where we stopped?",
    "Nice to have you back{name}. Pick up where we left off, or something new?",
    "Hi again{name}. Ready to carry on from our last conversation?",
)
# Said when they opened the conversation on a subject: each names the subject
# back so they know the button they pressed was understood.
GREETINGS_TOPIC = (
    "Hello{name}. You wanted to talk about {topic}. Where shall we start?",
    "Hi{name}. Let's look at {topic}. What would you like to start with?",
    "Hello{name}. {topic} it is. What would be most useful to go over first?",
    "Hi{name}. You picked {topic}. Is there a part of it you find tricky?",
    "Hello{name}. Let's talk about {topic}. What do you already know about it?",
    "Hi{name}. {topic} is a good one to revise. Where would you like to begin?",
    "Hello{name}. Shall we work through {topic} together? Tell me where to start.",
)


async def render_dashboard_session(
    session: AsyncSession,
    *,
    session_type: str,
    user_id: uuid.UUID,
    now: datetime,
    client: Mapping[str, Any] | None = None,
    topic: Mapping[str, str] | None = None,
    renderer: TutorPromptRenderer | None = None,
) -> dict[str, Any] | None:
    """The tutor's instructions, greeting and tools — or `None` for any other kind.

    Returning `None` rather than raising is what lets this stay one call:
    `assistant` asks about every session it starts and keeps its own
    placeholder text for the three kinds this slice has nothing to say about.
    """
    if session_type != DASHBOARD:
        return None

    brief = await service_brief.compose(session, user_id=user_id, now=now, client=client, topic=topic)
    try:
        instructions = (renderer or _renderer()).render(brief=brief, labels=LABELS)
    except RenderFailed as exc:
        # Not fatal: a dashboard session with the placeholder instructions is a
        # worse conversation, and one that refuses to start is no conversation.
        log.warning("tutor prompt not rendered", user_id=str(user_id), error=str(exc))
        return None

    return {
        "instructions": instructions,
        "greeting": greeting_for(brief, seed=f"{user_id}:{now.isoformat()}"),
        "tools": [dict(tool) for tool in CATALOG],
        "extras": {},
    }


def greeting_for(brief: Mapping[str, Any], *, seed: str) -> str:
    """The opening line: on their topic, returning or first-time, with their first name when known.

    ``seed`` names the session, so one session's line is stable and the next one's varies.
    """
    rng = random.Random(seed)  # noqa: S311 - picks a greeting, nothing secret
    full_name = str((brief.get("learner") or {}).get("name") or "").split()
    name_slot = f", {full_name[0]}" if full_name else ""
    topic_title = str((brief.get("topic") or {}).get("title") or "").rstrip(" .?!")
    if topic_title:
        return rng.choice(GREETINGS_TOPIC).format(name=name_slot, topic=topic_title)
    template = rng.choice(GREETINGS_RETURNING) if brief.get("last_conversation") else GREETING_FIRST_TIME
    return template.format(name=name_slot)


def _renderer() -> TutorPromptRenderer:
    """The default renderer, imported lazily so a test can pass its own instead."""
    from app.features.tutor_memory.renderer import build_renderer

    return build_renderer()
