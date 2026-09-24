"""Turning `MediaItem` rows into `MediaRead`, for one row or a whole page.

Split out of `service.py`, which keeps the writes, the publish rules and the
decision about whose body a reader may see. The projection is the only place
that knows two of the read model's fields are not columns — `specialty` and
`updated_at` both live inside the document-shaped `content` — and it has no
opinion about who may ask. Keeping the two apart is what holds the slice under
the shape guard's cap.
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
    session: AsyncSession, row: MediaItem, *, unlocked_exam_ids: frozenset[uuid.UUID] | None = None
) -> MediaRead:
    return (await read_many(session, [row], unlocked_exam_ids=unlocked_exam_ids))[0]


async def read_many(
    session: AsyncSession,
    rows: list[MediaItem],
    *,
    unlocked_exam_ids: frozenset[uuid.UUID] | None = None,
) -> list[MediaRead]:
    """The items, with their bodies only for a reader entitled to them.

    `unlocked_exam_ids` is `None` for a caller that has already decided the
    reader may see everything — a platform admin, on authoring routes and on
    the public listing (the episode player loads its playlist from the list).
    For everybody else it is the set of exams they hold a **live** grant for,
    and an item belonging to any other exam comes back locked. Material with
    no exam at all is free material and is never locked.

    Exam codes are fetched for the whole page at once: a listing resolved them
    one row at a time, which was a hundred queries for a hundred-item page.

    `specialty` is derived whether or not the body is withheld. It is a
    catalogue facet in the same family as `kind`, `title` and `exam_code` — all
    of which are already public — and a locked deck that reports no specialty
    disappears from the facet list on the very screen that offers to unlock it.
    The body itself is still gated.
    """
    codes = await catalog.exam_codes_by_id(session, [row.exam_id for row in rows if row.exam_id])
    out: list[MediaRead] = []
    for row in rows:
        content = dict(row.content or {})
        locked = _locked(row, unlocked_exam_ids)
        out.append(
            MediaRead(
                id=row.id,
                kind=row.kind,
                slug=row.slug,
                title=row.title,
                summary=row.summary,
                content=None if locked else content,
                locked=locked,
                exam_code=codes.get(row.exam_id) if row.exam_id else None,
                specialty=domain.specialty_of(content),
                status=row.status,
                created_at=row.created_at,
                published_at=row.published_at,
                updated_at=updated_at(row, content),
            )
        )
    return out


def updated_at(row: MediaItem, content: dict[str, Any]) -> datetime:
    """When this material last changed.

    The document's own `updated_at` first: that is the date the authoring tool
    wrote and the one the retiring client's blog cards printed, so a migrated
    item keeps the day it was edited in b2c instead of the day it was imported
    here. The row's own `updated_at` after it, which is the truth for anything
    authored in this backend and is `created_at` for a row nobody has edited —
    a non-nullable column, so the chain ends there rather than falling through
    to `published_at`.
    """
    return domain.content_updated_at(content) or row.updated_at


def _locked(row: MediaItem, unlocked_exam_ids: frozenset[uuid.UUID] | None) -> bool:
    """Whether the body is withheld: material for an exam the reader does not hold."""
    if unlocked_exam_ids is None or row.exam_id is None:
        return False
    return row.exam_id not in unlocked_exam_ids
