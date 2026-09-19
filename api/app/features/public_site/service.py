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

from app.core.errors import AppError, raise_mapped
from app.core.redis import get_redis
from app.features.attempts import service_reads as attempts
from app.features.identity import service as identity
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
    cached = await _cached()
    if cached is not None:
        return cached

    figures = schemas.SiteStatistics(
        consultations=await attempts.count_consultations(session),
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
    try:
        kind = domain.normalise_kind(body.kind)
        domain.ensure_sendable(
            name=body.name or "", email=body.email or "", body=body.body, kind=kind
        )
    except domain.InvalidMessage as exc:
        raise_mapped(exc, _REFUSALS)

    row = await repository.add_message(
        session,
        kind=kind.value,
        name=domain.clean(body.name) or None,
        email=domain.clean(body.email) or None,
        subject=domain.clean(body.subject) or None,
        body=domain.clean(body.body),
        source=domain.clean(body.source) or None,
        user_id=user_id,
    )
    return schemas.MessageAccepted(id=row.id, kind=row.kind)


async def list_messages(
    session: AsyncSession, *, kind: str | None, limit: int
) -> list[schemas.MessageRead]:
    rows = await repository.list_messages(session, kind=kind, limit=limit)
    return [_read(row) for row in rows]


async def mark_handled(
    session: AsyncSession, *, message_id: uuid.UUID, by: uuid.UUID, at: datetime
) -> schemas.MessageRead:
    row = await repository.mark_handled(session, message_id=message_id, by=by, at=at)
    if row is None:
        raise errors.MessageNotFound()
    return _read(row)


def _read(row: object) -> schemas.MessageRead:
    return schemas.MessageRead.model_validate(row, from_attributes=True)
