"""Runs the media library's rules against the database: authoring, publishing and listing
study material, and mapping the domain's plain exceptions onto the API's error codes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, raise_mapped
from app.core.jobs import defer_in_transaction
from app.core.ports import VectorIndex
from app.features.catalog.service import resolve_exam
from app.features.media import domain, errors, repository, service_reads
from app.features.media.models import MediaItem
from app.features.media.schemas import MediaRead

# Owned by tutor_memory/jobs.py; named here as a string so media does not import that module (cycle).
_TUTOR_REINDEX_MEDIA_TASK = "reindex_media_item"
_TUTOR_MATERIAL_QUEUE = "material"

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
    """Creates a new draft, refusing an unknown kind, an unusable title, or a slug already taken."""
    try:
        media_kind = domain.normalize_kind(kind)
        slug = domain.slugify(title)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    if await repository.by_slug(session, slug) is not None:
        raise errors.SlugTaken()

    exam_id = (await resolve_exam(session, exam_code)).id if exam_code else None
    item = await repository.create(
        session,
        kind=media_kind,
        slug=slug,
        title=title.strip(),
        summary=summary,
        content=content,
        specialty=domain.specialty_of(content),
        exam_id=exam_id,
        author_id=author_id,
    )
    return await service_reads.read_one(session, item, with_review=True)


async def update(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    title: str | None,
    summary: str | None,
    content: dict[str, Any] | None,
) -> MediaRead:
    """Replaces the given fields on a draft, leaving the others as they were. Refuses once published."""
    item = await _require(session, item_id)
    try:
        domain.ensure_editable(status=item.status)
    except domain.NotEditable as exc:
        raise_mapped(exc, _REFUSALS)

    values: dict[str, Any] = {}
    if title is not None:
        values["title"] = title.strip()
    if summary is not None:
        values["summary"] = summary
    if content is not None:
        # Imported here, not at the top: media_production is built on this slice, and what counts
        # as running is its to say.
        from app.features.media_production import service as production

        if production.is_running(dict(item.content or {})):
            raise errors.BeingProduced()
        values["content"] = content
        values["specialty"] = domain.specialty_of(content)
    if values:
        await repository.update_item(session, item_id, **values)
    return await service_reads.read_one(session, await _require(session, item_id), with_review=True)


async def publish(
    session: AsyncSession, item_id: uuid.UUID, *, index: VectorIndex, now: datetime
) -> MediaRead:
    """Publish, and make it findable.

    Indexed on publish rather than on write: a draft nobody can read should not
    surface in search.
    """
    item = await _require(session, item_id)
    try:
        status = domain.publish(status=item.status)
    except domain.AlreadyPublished as exc:
        raise_mapped(exc, _REFUSALS)

    await repository.update_item(session, item_id, status=status, published_at=now)
    await index.index(
        doc_id=str(item.id),
        text=f"{item.title}\n{item.summary or ''}",
        metadata={"kind": item.kind, "slug": item.slug},
    )
    await defer_in_transaction(
        session,
        queue=_TUTOR_MATERIAL_QUEUE,
        task=_TUTOR_REINDEX_MEDIA_TASK,
        queueing_lock=f"reindex-media:{item_id}",
        args={"media_item_id": str(item_id)},
    )
    return await service_reads.read_one(
        session, await _require(session, item_id), unlocked_exam_ids=None, with_review=True
    )


async def read_by_id(session: AsyncSession, item_id: uuid.UUID, *, viewer_is_admin: bool) -> MediaRead:
    """One item by its primary key, refusing a draft to anyone but a platform admin."""
    item = await _require(session, item_id)
    if not domain.is_public(status=item.status) and not viewer_is_admin:
        raise errors.ItemNotFound()
    unlocked = None if viewer_is_admin else frozenset[uuid.UUID]()
    return await service_reads.read_one(
        session, item, unlocked_exam_ids=unlocked, with_review=viewer_is_admin
    )


async def read_by_slug(
    session: AsyncSession,
    slug: str,
    *,
    viewer_is_admin: bool,
    unlocked: frozenset[uuid.UUID] = frozenset(),
) -> MediaRead:
    """One item by its URL slug, refusing a draft to anyone but a platform admin."""
    item = await repository.by_slug(session, slug)
    if item is None or (not domain.is_public(status=item.status) and not viewer_is_admin):
        # 404 for an unpublished draft: its existence is not public either.
        raise errors.ItemNotFound()
    return await service_reads.read_one(
        session, item, unlocked_exam_ids=None if viewer_is_admin else unlocked
    )


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
    specialty: str | None = None,
    has_specialty: bool | None = None,
    sort: str = "created",
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
    narrowed: dict[str, Any] = {
        "kind": kind,
        "statuses": statuses,
        "exam_id": exam_id,
        "search": search,
        "specialty": (specialty or "").strip() or None,
        "has_specialty": has_specialty,
        "sort": sort,
    }
    records, next_cursor = await repository.list_catalog(session, limit=limit, cursor=cursor, **narrowed)
    total = await repository.count_catalog(session, **narrowed)
    # Staff listing the public catalogue still get bodies: a slug read already
    # unlocks for admins, and the episode player loads its playlist from this
    # list. Locking the list while unlocking the page made every episode
    # render as "no audio attached".
    read_unlocked = None if viewer_is_admin else unlocked
    items = await service_reads.read_many(session, records, unlocked_exam_ids=read_unlocked)
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
    """Deletes a draft outright, refusing once the item has been published."""
    item = await _require(session, item_id)
    try:
        domain.ensure_deletable(status=item.status)
    except domain.NotDeletable as exc:
        raise_mapped(exc, _REFUSALS)
    await repository.delete_item(session, item_id)


async def _require(session: AsyncSession, item_id: uuid.UUID) -> MediaItem:
    """The stored item, refusing with `ItemNotFound` if the id matches nothing."""
    item = await repository.by_id(session, item_id)
    if item is None:
        raise errors.ItemNotFound()
    return item


# --- The body of a media item, as the AV production jobs need it.


@dataclass(frozen=True)
class ProductionItem:
    """The subset of a media item's fields the AV production jobs need, decoupled from the ORM row."""

    id: uuid.UUID
    kind: str
    title: str
    content: dict[str, Any]
    exam_id: uuid.UUID | None
    # False once published: a published item is replaced, never rewritten in place.
    editable: bool = True


async def production_item(session: AsyncSession, item_id: uuid.UUID, *, lock: bool = False) -> ProductionItem:
    """One item's production-relevant fields, refusing with `ItemNotFound` if the id matches nothing.

    `lock` keeps anyone else from rewriting the item until this transaction ends.
    """
    item = await repository.by_id(session, item_id, lock=lock)
    if item is None:
        raise errors.ItemNotFound()
    return ProductionItem(
        id=item.id,
        kind=item.kind,
        title=item.title,
        content=dict(item.content or {}),
        exam_id=item.exam_id,
        editable=domain.is_editable(status=item.status),
    )


async def replace_content(session: AsyncSession, item_id: uuid.UUID, content: dict[str, Any]) -> None:
    """Overwrites an item's stored body, used by the AV production jobs to attach rendered media."""
    await repository.update_item(session, item_id, content=content, specialty=domain.specialty_of(content))
