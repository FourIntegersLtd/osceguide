"""Turning `MediaItem` rows into `MediaRead`, for one row or a whole page.

Writes, publish rules and the decision about whose body a reader may see live
in `service.py`. This module knows one of the read model's fields is not a
column — `updated_at` may come from inside the document-shaped `content`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import service as catalog
from app.features.media import domain
from app.features.media.models import MediaItem
from app.features.media.schemas import MediaRead


async def read_one(
    session: AsyncSession, item: MediaItem, *, unlocked_exam_ids: frozenset[uuid.UUID] | None = None
) -> MediaRead:
    """One stored item, shaped into what a route returns."""
    return (await read_many(session, [item], unlocked_exam_ids=unlocked_exam_ids))[0]


async def read_many(
    session: AsyncSession,
    items: list[MediaItem],
    *,
    unlocked_exam_ids: frozenset[uuid.UUID] | None = None,
) -> list[MediaRead]:
    """The items, with their bodies only for a reader entitled to them.

    `unlocked_exam_ids` is `None` for a caller that has already decided the
    reader may see everything — a platform admin, authoring routes, and the
    public listing. For everybody else it is the set of exams they hold a
    **live** grant for; an item belonging to any other exam comes back
    locked. Material with no exam at all is free and never locked.

    Exam codes are fetched for the whole page at once, avoiding one query per
    item.

    `specialty` is its own column, returned whether or not the body is
    withheld — it is a public catalogue facet like `kind` and `title`, so a
    locked item still needs it to appear on a facet list, and filing one no
    longer means reading the body it is about to hide.
    """
    codes = await catalog.exam_codes_by_id(session, [item.exam_id for item in items if item.exam_id])
    reads: list[MediaRead] = []
    for item in items:
        content = dict(item.content or {})
        locked = _locked(item, unlocked_exam_ids)
        reads.append(
            MediaRead(
                id=item.id,
                kind=item.kind,
                slug=item.slug,
                title=item.title,
                summary=item.summary,
                content=None if locked else content,
                locked=locked,
                exam_code=codes.get(item.exam_id) if item.exam_id else None,
                specialty=item.specialty,
                status=item.status,
                created_at=item.created_at,
                published_at=item.published_at,
                updated_at=updated_at(item, content),
            )
        )
    return reads


def updated_at(item: MediaItem, content: dict[str, Any]) -> datetime:
    """When this material last changed.

    The document's own `updated_at` first, so a migrated item keeps its
    original edit date rather than the day it was imported. Otherwise the
    item's own `updated_at`, which is `created_at` for an item nobody has edited.
    """
    return domain.content_updated_at(content) or item.updated_at


def _locked(item: MediaItem, unlocked_exam_ids: frozenset[uuid.UUID] | None) -> bool:
    """Whether the body is withheld: material for an exam the reader does not hold."""
    if unlocked_exam_ids is None or item.exam_id is None:
        return False
    return item.exam_id not in unlocked_exam_ids
