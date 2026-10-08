"""What an anonymous visitor may send us, and what they may be told.

The statistics are cached because the landing page is the busiest thing on the
site and none of its numbers changes meaningfully between two views. Every
count is asked of the slice that owns the rows — this slice reads no table but
its own.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Principal
from app.core.errors import AppError, raise_mapped
from app.core.pagination import CursorParams, Page
from app.core.redis import get_redis
from app.features.attempts import service_reads as attempts
from app.features.identity import service as identity
from app.features.inbox import service as inbox
from app.features.public_site import domain, errors, repository, schemas
from app.features.stations import service_reads as stations

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.InvalidMessage: errors.InvalidMessageError,
}

_CACHE_KEY = "public_site:statistics"
# Long enough that a burst of landing views costs one set of counts, short
# enough that a number nobody recognises is gone within the hour.
_CACHE_SECONDS = 600


async def statistics(session: AsyncSession, *, now: datetime) -> schemas.SiteStatistics:
    """The landing page's counters, from the cache when there is one, else freshly counted."""
    cached = await _cached()
    if cached is not None:
        return cached

    figures = schemas.SiteStatistics(
        consultations=await attempts.count_consultations(session),
        feedback=await attempts.count_feedback(session),
        debriefs=await attempts.count_debriefs(session),
        users=await identity.count_users(session),
        # The platform catalogue, not an institution's own material: this is
        # the number on our front page and their stations are not ours to count.
        stations=await stations.count_stations(session, None),
        as_of=now,
    )
    await _remember(figures)
    return figures


async def _cached() -> schemas.SiteStatistics | None:
    """The last remembered statistics, or `None` on a miss, a stale shape or a cache that is down."""
    redis = get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_CACHE_KEY)
    except Exception:  # noqa: BLE001 - a cache that is down is not an outage
        return None
    if not raw:
        return None
    try:
        return schemas.SiteStatistics.model_validate(json.loads(raw))
    except Exception:  # noqa: BLE001 - a stale shape is a miss, not a failure
        return None


async def _remember(figures: schemas.SiteStatistics) -> None:
    """Cache freshly counted statistics, tolerating a cache that is down."""
    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.setex(_CACHE_KEY, _CACHE_SECONDS, figures.model_dump_json())
    except Exception:  # noqa: BLE001 - see above
        return


async def send(
    session: AsyncSession, body: schemas.SendMessage, *, user_id: uuid.UUID | None
) -> schemas.MessageAccepted:
    """Validate and store a contact or feedback message, filing it against the sender when signed in."""
    try:
        kind = domain.normalise_kind(body.kind)
        domain.ensure_sendable(name=body.name or "", email=body.email or "", body=body.body, kind=kind)
    except domain.InvalidMessage as exc:
        raise_mapped(exc, _REFUSALS)

    message = await repository.add_message(
        session,
        kind=kind.value,
        name=domain.clean(body.name) or None,
        email=domain.clean(body.email) or None,
        subject=domain.clean(body.subject) or None,
        body=domain.clean(body.body),
        source=domain.clean(body.source) or None,
        user_id=user_id,
    )
    return schemas.MessageAccepted(id=message.id, kind=message.kind)


async def list_messages(
    session: AsyncSession, *, kind: str | None, handled: bool | None, params: CursorParams
) -> Page[schemas.MessageRead]:
    """The platform-admin inbox, one page at a time, newest first, narrowed by kind and handled state."""
    messages, next_cursor = await repository.list_messages(session, kind=kind, handled=handled, params=params)
    return Page(items=[_read(message) for message in messages], next_cursor=next_cursor)


async def mark_handled(
    session: AsyncSession, *, message_id: uuid.UUID, by: uuid.UUID, at: datetime
) -> schemas.MessageRead:
    """Mark a message answered, refusing when no message has that id."""
    message = await repository.mark_handled(session, message_id=message_id, by=by, at=at)
    if message is None:
        raise errors.MessageNotFound()
    return _read(message)


async def reply(
    session: AsyncSession, *, message_id: uuid.UUID, body: str, actor: Principal, at: datetime
) -> schemas.MessageRead:
    """Answer a message in the sender's inbox and take it out of the queue.

    Marked handled first, which is also the lookup. A sender who was not signed in has no inbox, and
    the refusal rolls the request back, so nothing stays marked.
    """
    message = await repository.mark_handled(session, message_id=message_id, by=actor.user_id, at=at)
    if message is None:
        raise errors.MessageNotFound()
    if message.user_id is None:
        raise errors.CannotReplyInApp()
    await inbox.deliver_reply(
        session,
        actor=actor,
        site_message_id=message.id,
        recipient_id=message.user_id,
        original_subject=message.subject,
        body=body,
    )
    return _read(message)


def _read(message: object) -> schemas.MessageRead:
    return schemas.MessageRead.model_validate(message, from_attributes=True)
