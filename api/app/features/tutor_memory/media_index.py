"""The media search box, over the same pgvector store the tutor reads.

`media` reaches it through `service_search.media_title_index`. One index, two readers: the
tutor wants a passage it can quote, the search box wants the item. Two differences from
the tutor's reader, both deliberate:

- **No exam filter.** This returns titles of material that `GET /api/v1/media` already
  lists to every signed-in reader.
- **Items, not passages.** A document matches on its best passage, so the same summary
  cannot fill the results with six of its own paragraphs.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import VectorIndex
from app.features.tutor_memory import repository_index
from app.features.tutor_memory.chunking import chunk
from app.features.tutor_memory.embedder import build_embedder

log = get_logger(__name__)

# How many passages to consider before folding them down to items. A document
# can contribute several, so asking for exactly `limit` passages would return
# fewer than `limit` items whenever one of them matched twice.
_PASSAGE_FACTOR = 4


class PgVectorMediaIndex:
    """`core.ports.VectorIndex` over `material_chunks`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def index(self, *, doc_id: str, text: str, metadata: dict[str, str]) -> None:
        """Make one item findable the moment it is published, rather than waiting for the
        nightly re-index."""
        corpus = metadata.get("kind")
        if not corpus:
            log.warning("media item indexed without a kind", doc_id=doc_id)
            return
        try:
            embedder = build_embedder()
        except Exception as exc:  # noqa: BLE001 - publishing must not fail on the index
            log.info("media index not configured", doc_id=doc_id, error=str(exc))
            return
        passages = chunk(text)
        if not passages:
            await repository_index.forget_source(self._session, corpus=corpus, source_id=doc_id)
            return
        vectors = await embedder.embed([p.text for p in passages])
        await repository_index.replace_source(
            self._session,
            corpus=corpus,
            source_id=doc_id,
            exam_id=None,
            title=metadata.get("slug", ""),
            chunks=[
                {"index": p.index, "section": p.section, "text": p.text, "embedding": vector}
                for p, vector in zip(passages, vectors, strict=True)
            ],
        )

    async def search(self, *, query: str, limit: int) -> list[tuple[str, float]]:
        try:
            embedder = build_embedder()
        except Exception as exc:  # noqa: BLE001 - an unconfigured search finds nothing
            log.info("media search not configured", error=str(exc))
            return []
        vectors = await embedder.embed([query])
        rows = await repository_index.nearest(
            self._session,
            embedding=vectors[0],
            # No filter, deliberately, and spelled `None` rather than reached
            # by passing an empty list: see `media.service_search.get_vector_index`.
            exam_ids=None,
            corpus=None,
            limit=limit * _PASSAGE_FACTOR,
        )
        best: dict[str, float] = {}
        for row, score in rows:
            # Rows arrive best first, so the first sighting of a source is its
            # best passage and later ones are worse.
            best.setdefault(str(row.source_id), score)
        return list(best.items())[:limit]


def build_media_index(session: AsyncSession) -> VectorIndex:
    return PgVectorMediaIndex(session)
