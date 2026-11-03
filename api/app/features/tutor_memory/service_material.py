"""Building the material index: what goes into it, and what is retired from it.

What goes in decides what a citation can say, so the corpus names and titles are settled
here and read out by `service_search` unchanged.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.pagination import decode_cursor
from app.core.ports import MaterialIndex, SourcePassages
from app.features.assistant.schemas import HelpArticle
from app.features.media import service as media
from app.features.media.schemas import MediaRead
from app.features.stations import service_reads as stations
from app.features.tutor_memory import chunking
from app.features.tutor_memory.domain import HELP_CORPUS, MEDIA_KINDS

log = get_logger(__name__)

STATION_CORPUS = "station"
MEDIA_PAGE = 200

# Sources are handed to the index in groups of about this many passages, which is one
# embedding request's worth: a group's changed passages share a request instead of
# taking one per source, and no more than a group's vectors are ever held at once.
REINDEX_BATCH_PASSAGES = 96

# Three is what a spoken answer can carry. A fourth passage is not read out --
# it lengthens the prompt and gives the model more to blend into one
# undifferentiated paragraph with three citations after it.
SEARCH_LIMIT = 3

NOT_CONFIGURED = (
    "The material search is not available in this deployment. Say you cannot look that up "
    "right now, and answer from what you already know or offer to come back to it."
)

NOTHING_IN_MATERIAL = (
    "The material has nothing on that. Say you could not find it in their reading rather than "
    "answering from memory, and offer to come back to it."
)

# The card envelope the frontend parses. Bumped with the shape, never with the
# contents: `frontend/src/shared/livekit-ui-guidance/contracts.ts` validates it.
CARD_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class IndexRun:
    """What one re-index did, for the log line and the admin route's answer."""

    sources: int
    passages: int
    retired: int


async def reindex(session: AsyncSession, *, index: MaterialIndex | None = None) -> IndexRun:
    """Rebuild the index from the published material, and retire what has gone.

    Idempotent by construction: every source is upserted by `(corpus, id)` and
    anything indexed that is no longer published is dropped. A passage whose
    text has not changed keeps its vector, so running it twice embeds nothing
    the second time, and a run that failed half way is repaired by the next
    one rather than needing to be unwound.
    """
    from app.features.tutor_memory.index import NoMaterialIndex, build_material_index

    # Nothing configured: walk the material, index none of it, and say so in
    # the log rather than failing a nightly job on every deployment without a key.
    index = index or build_material_index(session) or NoMaterialIndex()
    sources = passages = 0
    seen: dict[str, set[str]] = {corpus: set() for corpus in (STATION_CORPUS, *MEDIA_KINDS, HELP_CORPUS)}

    batch: list[SourcePassages] = []
    async for source in _published_sources(session):
        seen[source.corpus].add(source.source_id)
        batch.append(source)
        sources += 1
        if sum(len(held.chunks) for held in batch) >= REINDEX_BATCH_PASSAGES:
            passages += await _index_batch(index, batch)
            batch = []
    passages += await _index_batch(index, batch)

    retired = await _retire(index, seen)
    log.info("material reindexed", sources=sources, passages=passages, retired=retired)
    return IndexRun(sources=sources, passages=passages, retired=retired)


async def reindex_media_item(
    session: AsyncSession, media_item_id: uuid.UUID, *, index: MaterialIndex | None = None
) -> int:
    """Index one published media item into the tutor material index, if it belongs there.

    Does not retire other sources — that is only safe on a full re-index walk.
    """
    from app.features.catalog import service as catalog  # avoids an import cycle
    from app.features.tutor_memory.index import NoMaterialIndex, build_material_index

    read = await media.read_by_id(session, media_item_id, viewer_is_admin=True)
    if read.status != "published":
        return 0

    material_index = index or build_material_index(session) or NoMaterialIndex()
    exam_id: str | None = None
    if read.exam_code:
        exam_id = str((await catalog.resolve_exam(session, read.exam_code)).id)
    return await _index_published_media_item(material_index, media_item=read, exam_id=exam_id)


async def _index_published_media_item(
    index: MaterialIndex, *, media_item: MediaRead, exam_id: str | None
) -> int:
    """Hand one published media item to the index when its kind is tutor-searchable."""
    if media_item.kind not in MEDIA_KINDS:
        return 0
    return await _index_one(
        index,
        corpus=media_item.kind,
        source_id=str(media_item.id),
        exam_id=exam_id,
        title=media_item.title,
        text=_media_index_text(media_item),
    )


def _media_index_text(media_item: MediaRead) -> str:
    """Prose the chunker sees for one media item — summary plus body."""
    return " ".join(part for part in (media_item.summary, _content_text(media_item.content)) if part)


async def _index_one(
    index: MaterialIndex, *, corpus: str, source_id: str, exam_id: str | None, title: str, text: str
) -> int:
    """Chunk one source's text and hand the chunks to the index."""
    return await _index_batch(
        index, [_passages(corpus=corpus, source_id=source_id, exam_id=exam_id, title=title, text=text)]
    )


async def _index_batch(index: MaterialIndex, batch: list[SourcePassages]) -> int:
    """Hand a group of sources to the index, and name them if it stops there.

    A re-index that died used to leave nothing in the log to say what it was reading.
    """
    if not batch:
        return 0
    try:
        return await index.upsert_many(batch)
    except BaseException:
        log.error(
            "material reindex stopped",
            sources=[f"{source.corpus}:{source.source_id} {source.title}" for source in batch],
        )
        raise


def _passages(*, corpus: str, source_id: str, exam_id: str | None, title: str, text: str) -> SourcePassages:
    """One source's text cut into the passages the index stores."""
    return SourcePassages(
        corpus=corpus,
        source_id=source_id,
        exam_id=exam_id,
        title=title,
        chunks=[
            {"index": chunk.index, "section": chunk.section, "text": chunk.text}
            for chunk in chunking.chunk(text)
        ],
    )


async def _published_sources(session: AsyncSession) -> AsyncIterator[SourcePassages]:
    """Everything the index should hold, cut into passages: stations, then media, then help."""
    for station in await stations.published_material(session):
        yield _passages(
            corpus=STATION_CORPUS,
            source_id=str(station.version_id),
            exam_id=str(station.exam_id) if station.exam_id else None,
            title=station.title,
            text=station.text,
        )

    for media_item, exam_id in await _published_media(session):
        if media_item.kind not in MEDIA_KINDS:
            continue
        yield _passages(
            corpus=media_item.kind,
            source_id=str(media_item.id),
            exam_id=exam_id,
            title=media_item.title,
            text=_media_index_text(media_item),
        )

    for source_id, exam_id, article in await _help_sources(session):
        yield _passages(
            corpus=HELP_CORPUS,
            source_id=source_id,
            exam_id=exam_id,
            title=article.title,
            text=" ".join(part for part in (article.summary, article.body_md) if part),
        )


async def _help_sources(session: AsyncSession) -> list[tuple[str, str | None, HelpArticle]]:
    """Each help article as the sources it is indexed under: `(source_id, exam_id, article)`.

    An article for every exam is one source with no exam, reachable by anyone.
    One written for particular exams is a source per exam, `<slug>@<code>`, so
    it reaches only the people who hold that exam — the same article the help
    browser shows them. An exam this deployment does not have is skipped.
    """
    from app.features.assistant import service_help  # avoids an import cycle
    from app.features.catalog import service as catalog

    help_sources: list[tuple[str, str | None, HelpArticle]] = []
    for article in service_help.all_articles():
        if "all" in article.exam_codes:
            help_sources.append((article.slug, None, article))
            continue
        for exam_code in article.exam_codes:
            exam = await catalog.exam_read_by_code(session, exam_code)
            if exam is not None:
                help_sources.append((f"{article.slug}@{exam_code}", str(exam.id), article))
    return help_sources


async def _retire(index: MaterialIndex, seen: dict[str, set[str]]) -> int:
    """Drop passages of anything that is indexed but no longer published.

    An unpublished summary that stayed in the index is the failure worth
    preventing: the tutor would go on quoting it, with a citation to a page
    that now returns a 404. Goes through the port rather than the repository
    directly, so this walk can be exercised against a fake.
    """
    retired = 0
    for corpus, live in seen.items():
        for source_id in await index.indexed_sources(corpus=corpus):
            if source_id not in live:
                retired += await index.forget(corpus=corpus, source_id=source_id)
    return retired


async def _published_media(session: AsyncSession) -> list[tuple[MediaRead, str | None]]:
    """Every published media item, with the exam it belongs to, in one walk."""
    from app.features.catalog import service as catalog  # avoids an import cycle

    media_with_exam: list[tuple[MediaRead, str | None]] = []
    codes: dict[str, uuid.UUID] = {}
    cursor: dict[str, Any] | None = None
    while True:
        published_items, next_cursor = await media.list_published(
            session, kind=None, limit=MEDIA_PAGE, cursor=cursor
        )
        for media_item in published_items:
            exam_id: str | None = None
            if media_item.exam_code:
                if media_item.exam_code not in codes:
                    codes[media_item.exam_code] = (
                        await catalog.resolve_exam(session, media_item.exam_code)
                    ).id
                exam_id = str(codes[media_item.exam_code])
            media_with_exam.append((media_item, exam_id))
        if not next_cursor:
            return media_with_exam
        # The service takes a decoded cursor; the encoded one is the router's
        # currency, and this caller is not a router.
        cursor = decode_cursor(next_cursor)


_LINK = re.compile(r"https?://\S+")


def _content_text(content: object) -> str:
    """Whatever prose a media item's body holds, flattened.

    Links are left out: a body reads back with signed file links, and one in the index would put a
    working two-hour link in front of the tutor and the assistant for every learner.
    """
    if isinstance(content, str):
        return _LINK.sub("", content).strip()
    if isinstance(content, dict):
        return " ".join(_content_text(entry) for entry in content.values()).strip()
    if isinstance(content, list):
        return " ".join(_content_text(entry) for entry in content).strip()
    return ""
