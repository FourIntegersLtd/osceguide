"""Authoring, publishing and searching study material."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.core.ports import VectorIndex
from app.features.catalog.service import resolve_exam
from app.features.media import domain, errors, repository, service_reads
from app.features.media.models import MediaItem
from app.features.media.schemas import MediaRead

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.UnknownMediaKind: errors.UnknownMediaKindError,
    domain.NotEditable: errors.NotEditableError,
    domain.AlreadyPublished: errors.AlreadyPublishedError,
    domain.UnusableTitle: errors.UnusableTitleError,
    domain.EmptyQuery: errors.EmptyQueryError,
    domain.QueryTooLong: errors.EmptyQueryError,
    domain.InvalidListStatus: errors.InvalidListStatusError,
    domain.NotDeletable: errors.NotDeletableError,
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
    return await service_reads.read_one(session, row)


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
    return await service_reads.read_one(session, await _require(session, item_id))


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
    return await service_reads.read_one(session, await _require(session, item_id), unlocked_exam_ids=None)


async def read_by_id(session: AsyncSession, item_id: uuid.UUID, *, viewer_is_admin: bool) -> MediaRead:
    row = await _require(session, item_id)
    if not domain.is_public(status=row.status) and not viewer_is_admin:
        raise errors.ItemNotFound()
    unlocked = None if viewer_is_admin else frozenset[uuid.UUID]()
    return await service_reads.read_one(session, row, unlocked_exam_ids=unlocked)


async def read_by_slug(
    session: AsyncSession,
    slug: str,
    *,
    viewer_is_admin: bool,
    unlocked: frozenset[uuid.UUID] = frozenset(),
) -> MediaRead:
    row = await repository.by_slug(session, slug)
    if row is None or (not domain.is_public(status=row.status) and not viewer_is_admin):
        # 404 for an unpublished draft: its existence is not public either.
        raise errors.ItemNotFound()
    return await service_reads.read_one(session, row, unlocked_exam_ids=None if viewer_is_admin else unlocked)


async def list_catalog(
    session: AsyncSession,
    *,
    kind: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    status: str | None,
    viewer_is_admin: bool,
    exam_code: str | None = None,
    search: str | None = None,
    unlocked: frozenset[uuid.UUID] = frozenset(),
) -> tuple[list[MediaRead], str | None, int]:
    """A page of the catalogue, what comes after it, and how many items match.

    `exam_code` and `search` are applied here, not by the browser. An exam
    code that names no published exam is refused, the way `POST /media`
    refuses it, rather than quietly answering with the free material alone.

    The count is of everything the filters match, cursor aside.
    """
    if kind:
        try:
            kind = domain.normalize_kind(kind)
        except domain.UnknownMediaKind as exc:
            raise_mapped(exc, _REFUSALS)
    statuses: tuple[str, ...] | None = None
    if viewer_is_admin and status:
        try:
            statuses = domain.parse_authoring_status(status)
        except domain.InvalidListStatus as exc:
            raise_mapped(exc, _REFUSALS)
    exam_id = (await resolve_exam(session, exam_code)).id if exam_code else None
    narrowed: dict[str, Any] = {"kind": kind, "statuses": statuses, "exam_id": exam_id, "search": search}
    rows, next_cursor = await repository.list_catalog(session, limit=limit, cursor=cursor, **narrowed)
    total = await repository.count_catalog(session, **narrowed)
    # Staff listing the public catalogue still get bodies: a slug read already
    # unlocks for admins, and the episode player loads its playlist from this
    # list. Locking the list while unlocking the page made every episode
    # render as "no audio attached".
    read_unlocked = None if viewer_is_admin else unlocked
    items = await service_reads.read_many(session, rows, unlocked_exam_ids=read_unlocked)
    return items, next_cursor, total


async def list_published(
    session: AsyncSession,
    *,
    kind: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    unlocked: frozenset[uuid.UUID] = frozenset(),
) -> tuple[list[MediaRead], str | None]:
    """The consumer catalogue, for a caller that walks it rather than showing it.

    No count: the tutor's material index reads every page in turn and has no
    screen to tell a total to.
    """
    items, next_cursor, _ = await list_catalog(
        session,
        kind=kind,
        limit=limit,
        cursor=cursor,
        status=None,
        viewer_is_admin=False,
        unlocked=unlocked,
    )
    return items, next_cursor


async def delete_draft(session: AsyncSession, item_id: uuid.UUID) -> None:
    row = await _require(session, item_id)
    try:
        domain.ensure_deletable(status=row.status)
    except domain.NotDeletable as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.delete_item(session, item_id)


async def _require(session: AsyncSession, item_id: uuid.UUID) -> MediaItem:
    row = await repository.by_id(session, item_id)
    if row is None:
        raise errors.ItemNotFound()
    return row


# --- The body of a media item, as the AV production jobs need it.


@dataclass(frozen=True)
class ProductionItem:
    id: uuid.UUID
    kind: str
    title: str
    content: dict[str, Any]
    exam_id: uuid.UUID | None


async def production_item(session: AsyncSession, item_id: uuid.UUID) -> ProductionItem:
    row = await repository.by_id(session, item_id)
    if row is None:
        raise errors.ItemNotFound()
    return ProductionItem(
        id=row.id,
        kind=row.kind,
        title=row.title,
        content=dict(row.content or {}),
        exam_id=row.exam_id,
    )


async def replace_content(session: AsyncSession, item_id: uuid.UUID, content: dict[str, Any]) -> None:
    await repository.update_item(session, item_id, content=content)
