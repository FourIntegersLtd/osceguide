"""Authoring, publishing and searching study material."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, raise_mapped
from app.core.ports import VectorIndex
from app.features.catalog import service as catalog
from app.features.catalog.service import resolve_exam
from app.features.media import domain, errors, repository
from app.features.media.models import MediaItem
from app.features.media.schemas import MediaRead, SearchHit

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.UnknownMediaKind: errors.UnknownMediaKindError,
    domain.NotEditable: errors.NotEditableError,
    domain.AlreadyPublished: errors.AlreadyPublishedError,
    domain.UnusableTitle: errors.UnusableTitleError,
    domain.EmptyQuery: errors.EmptyQueryError,
    domain.QueryTooLong: errors.EmptyQueryError,
}


async def create(
    session: AsyncSession,
    *,
    kind: str,
    title: str,
    summary: str | None,
    content: dict[str, Any],
    exam_code: str | None,
    author_id: uuid.UUID,
) -> MediaRead:
    try:
        media_kind = domain.normalize_kind(kind)
        slug = domain.slugify(title)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    if await repository.by_slug(session, slug) is not None:
        raise errors.SlugTaken()

    exam_id = (await resolve_exam(session, exam_code)).id if exam_code else None
    row = await repository.create(
        session,
        kind=media_kind,
        slug=slug,
        title=title.strip(),
        summary=summary,
        content=content,
        exam_id=exam_id,
        author_id=author_id,
    )
    return await _read(session, row)


async def update(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    title: str | None,
    summary: str | None,
    content: dict[str, Any] | None,
) -> MediaRead:
    row = await _require(session, item_id)
    try:
        domain.ensure_editable(status=row.status)
    except domain.NotEditable as exc:
        raise_mapped(exc, _REFUSALS)

    values: dict[str, Any] = {}
    if title is not None:
        values["title"] = title.strip()
    if summary is not None:
        values["summary"] = summary
    if content is not None:
        values["content"] = content
    if values:
        await repository.update_item(session, item_id, **values)
    return await _read(session, await _require(session, item_id))


async def publish(
    session: AsyncSession, item_id: uuid.UUID, *, index: VectorIndex, now: datetime
) -> MediaRead:
    """Publish, and make it findable.

    Indexed on publish rather than on write: a draft nobody can read should not
    surface in search.
    """
    row = await _require(session, item_id)
    try:
        status = domain.publish(status=row.status)
    except domain.AlreadyPublished as exc:
        raise_mapped(exc, _REFUSALS)

    await repository.update_item(session, item_id, status=status, published_at=now)
    await index.index(
        doc_id=str(row.id),
        text=f"{row.title}\n{row.summary or ''}",
        metadata={"kind": row.kind, "slug": row.slug},
    )
    return await _read(session, await _require(session, item_id))


async def read_by_slug(session: AsyncSession, slug: str, *, viewer_is_admin: bool) -> MediaRead:
    row = await repository.by_slug(session, slug)
    if row is None or (not domain.is_public(status=row.status) and not viewer_is_admin):
        # 404 for an unpublished draft: its existence is not public either.
        raise errors.ItemNotFound()
    return await _read(session, row)


async def list_published(
    session: AsyncSession, *, kind: str | None, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[MediaRead], str | None]:
    if kind:
        try:
            kind = domain.normalize_kind(kind)
        except domain.UnknownMediaKind as exc:
            raise_mapped(exc, _REFUSALS)
    rows, next_cursor = await repository.list_published(session, kind=kind, limit=limit, cursor=cursor)
    return [await _read(session, r) for r in rows], next_cursor


async def search(
    session: AsyncSession, *, query: str, index: VectorIndex, limit: int = 10
) -> list[SearchHit]:
    """Search the index, then read the rows it named.

    The index holds ids and nothing else, so what a reader sees always comes
    from the database — an item unpublished since it was indexed cannot leak
    through a stale entry.
    """
    try:
        cleaned = domain.clean_query(query)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    hits = await index.search(query=cleaned, limit=limit)
    scores = {uuid.UUID(doc_id): score for doc_id, score in hits}
    rows = await repository.by_ids(session, list(scores))
    return sorted(
        (
            SearchHit(id=r.id, kind=r.kind, slug=r.slug, title=r.title, score=scores.get(r.id, 0.0))
            for r in rows
            if domain.is_public(status=r.status)
        ),
        key=lambda hit: hit.score,
        reverse=True,
    )


async def _require(session: AsyncSession, item_id: uuid.UUID) -> MediaItem:
    row = await repository.by_id(session, item_id)
    if row is None:
        raise errors.ItemNotFound()
    return row


async def _read(session: AsyncSession, row: MediaItem) -> MediaRead:
    exam_code = await catalog.exam_code_by_id(session, row.exam_id) if row.exam_id else None
    return MediaRead(
        id=row.id,
        kind=row.kind,
        slug=row.slug,
        title=row.title,
        summary=row.summary,
        content=dict(row.content or {}),
        exam_code=exam_code,
        status=row.status,
        published_at=row.published_at,
    )


def get_vector_index(session: Annotated[AsyncSession, Depends(get_session)]) -> VectorIndex:
    """The dependency the router wires. Overridden in tests with a fake.

    Takes the request's session because the index is in the same database:
    indexing on publish belongs in the transaction that published.
    """
    from app.features.media.index import build_vector_index  # noqa: PLC0415

    return build_vector_index(session)
