"""The adapter behind `core.ports.MaterialIndex`: pgvector, or nothing at all.

pgvector rather than a separate vector store. See ADR 0019.

`NoMaterialIndex` is the other half of the decision, not a stub: a deployment with no
embedding key has no index, and the tutor must say it cannot look something up rather than
answer from memory and sound just as certain.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import Embedder, MaterialIndex, Passage
from app.core.settings import get_settings
from app.features.tutor_memory import repository_index

log = get_logger(__name__)


class PgVectorMaterialIndex:
    """Passages in Postgres, retrieved by cosine distance.

    Holds the session it was built with, so a re-index that fails half way leaves no
    half-indexed document behind.
    """

    def __init__(self, session: AsyncSession, embedder: Embedder) -> None:
        self._session = session
        self._embedder = embedder

    async def upsert(
        self,
        *,
        corpus: str,
        source_id: str,
        exam_id: str | None,
        title: str,
        chunks: Sequence[Mapping[str, Any]],
    ) -> int:
        """Embed one document's chunks and replace whatever it previously indexed.

        No chunks means the source has gone or come back empty, so its old passages
        are forgotten instead.
        """
        if not chunks:
            return await repository_index.forget_source(self._session, corpus=corpus, source_id=source_id)

        vectors = await self._embedder.embed([str(chunk["text"]) for chunk in chunks])
        embedded = [
            {"index": chunk["index"], "section": chunk["section"], "text": chunk["text"], "embedding": vector}
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        return await repository_index.replace_source(
            self._session,
            corpus=corpus,
            source_id=source_id,
            exam_id=uuid.UUID(exam_id) if exam_id else None,
            title=title,
            chunks=embedded,
        )

    async def indexed_sources(self, *, corpus: str) -> set[str]:
        return await repository_index.indexed_source_ids(self._session, corpus=corpus)

    async def forget(self, *, corpus: str, source_id: str) -> int:
        return await repository_index.forget_source(self._session, corpus=corpus, source_id=source_id)

    async def search(
        self, *, query: str, exam_ids: Sequence[str], corpus: str | None, limit: int
    ) -> list[Passage]:
        """The nearest passages to `query`, restricted to exams the caller is entitled to."""
        if not exam_ids or not query.strip():
            return []

        vectors = await self._embedder.embed([query])
        if not vectors:
            return []

        matches = await repository_index.nearest(
            self._session,
            embedding=vectors[0],
            exam_ids=[uuid.UUID(exam_id) for exam_id in exam_ids],
            corpus=corpus,
            limit=limit,
        )
        return [
            Passage(
                corpus=chunk.corpus,
                source_id=chunk.source_id,
                title=chunk.title,
                text=chunk.text,
                section=chunk.section,
                score=score,
            )
            for chunk, score in matches
        ]


class NoMaterialIndex:
    """No index configured: nothing stored, nothing found, and said so once."""

    async def upsert(
        self,
        *,
        corpus: str,
        source_id: str,
        exam_id: str | None,
        title: str,
        chunks: Sequence[Mapping[str, Any]],
    ) -> int:
        """Log and do nothing: there is no index to write these chunks into."""
        log.info("material index not configured", corpus=corpus, source_id=source_id)
        return 0

    async def indexed_sources(self, *, corpus: str) -> set[str]:
        # Never "everything in the table": an unconfigured deployment must not
        # retire passages a configured one wrote. Doing nothing is the only
        # safe answer when there is no index to speak for.
        return set()

    async def forget(self, *, corpus: str, source_id: str) -> int:
        return 0

    async def search(
        self, *, query: str, exam_ids: Sequence[str], corpus: str | None, limit: int
    ) -> list[Passage]:
        return []


def build_material_index(session: AsyncSession) -> MaterialIndex | None:
    """The real index, or `None` where there is no key to embed with.

    `None` rather than `NoMaterialIndex`: the caller must tell "I could not look that up"
    apart from "I looked and the material does not say", which an empty result cannot do.
    `NoMaterialIndex` is still the right answer for a re-index, where doing nothing quietly
    is correct.
    """
    if not get_settings().openai_api_key:
        return None
    from app.features.tutor_memory.embedder import EmbeddingFailed, build_embedder  # noqa: PLC0415

    try:
        return PgVectorMaterialIndex(session, build_embedder())
    except EmbeddingFailed as exc:
        # A key that is set but unusable — the package missing, say. Same
        # answer as no key at all: the tutor says it cannot look that up. A
        # raise here would be a 500 on the worker's tool route, which the
        # model hears as a failure mid-sentence.
        log.warning("material index could not be built", error=str(exc))
        return None
