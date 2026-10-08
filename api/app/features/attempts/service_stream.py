"""Telling a candidate their marking has finished.

Marking is a background job that takes a minute or two of model time, so a
browser has to learn it is done somehow. b2c had an SSE endpoint and a poller
and a second poller behind that; this is the one stream, carrying the whole
attempt each time (ADR 0015), so the page renders from a frame rather than
diffing events.

The stream ends when the attempt reaches a terminal state, because there is
genuinely nothing more to say about it — a page left open overnight should
not hold a connection until the tab is closed.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.core.auth import Principal
from app.core.db import SessionOpener
from app.core.events import user_topic
from app.core.ports import EventBus
from app.core.sse import Snapshot, capped, event_stream
from app.features.attempts import domain, service_reads

# Once an attempt is here, nothing else will happen to it.
_TERMINAL = frozenset({domain.Status.EVALUATED, domain.Status.FAILED})


async def ensure_streamable(
    attempt_id: uuid.UUID, principal: Principal, *, open_session: SessionOpener
) -> None:
    """Refuse before a single byte is sent.

    A `StreamingResponse` has already answered 200 by the time its body runs,
    so an ownership check inside the generator turns "not yours" into a
    successful response that then dies mid-frame. The client sees a stream
    that opened and broke, which is indistinguishable from a network fault.
    """
    async with open_session() as session:
        await service_reads.read_attempt(
            session,
            attempt_id,
            requester_id=principal.user_id,
            is_admin=principal.is_platform_admin,
        )


def attempt_stream(
    attempt_id: uuid.UUID, principal: Principal, *, bus: EventBus, open_session: SessionOpener
) -> AsyncIterator[str]:
    """One attempt, pushed until it is marked.

    Subscribed by *user* rather than by attempt: a person has one page open
    at a time, the scoring job already announces on that topic, and a topic
    per attempt would mean the job knowing which of them anybody is watching.
    The cost is a frame when another of their attempts changes, which is a
    re-render of data the page already has.
    """

    async def snapshot() -> Snapshot:
        """The current frame: the whole attempt, and whether this is the last one."""
        async with open_session() as session:
            attempt = await service_reads.read_attempt(
                session,
                attempt_id,
                requester_id=principal.user_id,
                is_admin=principal.is_platform_admin,
            )
        return Snapshot(attempt.model_dump_json(), final=domain.Status(attempt.status) in _TERMINAL)

    topics = [user_topic(principal.user_id)]
    return capped(principal.user_id, event_stream(topics=topics, snapshot=snapshot, bus=bus))
