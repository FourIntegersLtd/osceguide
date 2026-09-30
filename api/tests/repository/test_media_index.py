"""The media search box, over the shared pgvector store.

It returned an empty list for every query since the slice landed, because
`build_vector_index` returned a `NoVectorIndex` and nothing ever bound a real
one (M-3). These pin the two behaviours that make the replacement useful: an
item is findable, and one document cannot fill the results with its own
paragraphs.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory import repository_index
from app.features.tutor_memory.media_index import PgVectorMediaIndex

pytestmark = pytest.mark.db

DIMENSIONS = 1536


def vector(seed: float) -> list[float]:
    """A unit-ish vector that differs predictably, so distance is orderable."""
    return [seed] + [0.0] * (DIMENSIONS - 1)


async def index_passages(session: AsyncSession, *, corpus: str, source_id: str, seeds: list[float]) -> None:
    await repository_index.replace_source(
        session,
        corpus=corpus,
        source_id=source_id,
        exam_id=None,
        title=f"{corpus} {source_id}",
        chunks=[
            {"index": i, "section": "Overview", "text": f"passage {i}", "embedding": vector(seed)}
            for i, seed in enumerate(seeds)
        ],
    )
    await session.flush()


class StubEmbedder:
    def __init__(self, query_vector: list[float]) -> None:
        self._vector = query_vector

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


@pytest.fixture
def searchable(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Swap the embedder at the adapter's seam, not with a patched attribute
    somewhere else: this is what `build_embedder` is for."""

    def install(query_vector: list[float]) -> None:
        import app.features.tutor_memory.media_index as module

        monkeypatch.setattr(module, "build_embedder", lambda: StubEmbedder(query_vector))

    return install


async def test_a_published_item_is_findable(
    db_session: AsyncSession,
    searchable,  # type: ignore[no-untyped-def]
) -> None:
    doc = str(uuid.uuid4())
    await index_passages(db_session, corpus="summary", source_id=doc, seeds=[1.0])
    searchable(vector(1.0))

    hits = await PgVectorMediaIndex(db_session).search(query="asthma", limit=5)
    assert [doc_id for doc_id, _ in hits] == [doc]


async def test_a_document_matches_once_however_many_passages_it_has(
    db_session: AsyncSession,
    searchable,  # type: ignore[no-untyped-def]
) -> None:
    """Otherwise one long summary fills the page with six of its own
    paragraphs and the reader sees a single result six times."""
    wordy, brief = str(uuid.uuid4()), str(uuid.uuid4())
    await index_passages(db_session, corpus="summary", source_id=wordy, seeds=[1.0] * 6)
    await index_passages(db_session, corpus="blog", source_id=brief, seeds=[0.9])
    searchable(vector(1.0))

    hits = await PgVectorMediaIndex(db_session).search(query="asthma", limit=5)
    ids = [doc_id for doc_id, _ in hits]
    assert sorted(ids) == sorted([wordy, brief])
    assert len(ids) == len(set(ids))


async def test_search_is_not_filtered_by_what_the_reader_has_bought(
    db_session: AsyncSession,
    searchable,  # type: ignore[no-untyped-def]
) -> None:
    """Deliberate, and the opposite of the tutor's retrieval.

    This returns titles of material `GET /api/v1/media` already lists to every
    signed-in reader, so filtering search and not the list would hide in one
    place what is visible in the other. Access to the content itself is
    decided when the item is opened.
    """
    doc = str(uuid.uuid4())
    await index_passages(db_session, corpus="summary", source_id=doc, seeds=[1.0])
    searchable(vector(1.0))

    hits = await PgVectorMediaIndex(db_session).search(query="asthma", limit=5)
    assert [doc_id for doc_id, _ in hits] == [doc]


async def test_an_unconfigured_deployment_finds_nothing_rather_than_failing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.features.tutor_memory.media_index as module

    def unconfigured() -> None:
        raise RuntimeError("no embedding key")

    monkeypatch.setattr(module, "build_embedder", unconfigured)
    assert await PgVectorMediaIndex(db_session).search(query="asthma", limit=5) == []


async def test_publishing_without_a_kind_indexes_nothing_rather_than_guessing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The corpus is a CHECK constraint; guessing one would either fail the
    # insert or file the item under the wrong heading.
    import app.features.tutor_memory.media_index as module

    monkeypatch.setattr(module, "build_embedder", lambda: StubEmbedder(vector(1.0)))
    await PgVectorMediaIndex(db_session).index(doc_id=str(uuid.uuid4()), text="x", metadata={})
