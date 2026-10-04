"""The material index against real pgvector: ranking, filtering and replacing.

Everything above this file uses `FakeMaterialIndex`, which matches substrings.
That is the right double for "does the slice filter by entitlement" and the
wrong one for "does the query use the index and order by distance" — so this
is the one place the real extension is exercised, and the one place a mistake
in the SQL can be caught.

The vectors are hand-written rather than embedded. Three dimensions of made-up
numbers make the expected ordering something a reader can work out, and an
embedding model in a test would make the assertion depend on what OpenAI
returned that day.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import SourcePassages
from app.features.tutor_memory import repository_index
from app.features.tutor_memory.index import PgVectorMaterialIndex
from app.features.tutor_memory.vector_column import EMBEDDING_DIMENSIONS
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db


def vector(*leading: float) -> list[float]:
    """A full-width vector whose first few components are the ones that matter."""
    return [*leading, *([0.0] * (EMBEDDING_DIMENSIONS - len(leading)))]


CHEST_PAIN = vector(1.0, 0.0, 0.0)
BREATHLESS = vector(0.9, 0.4, 0.0)
ANXIETY = vector(0.0, 1.0, 0.0)


class ScriptedEmbedder:
    """Returns a prepared vector per text, so the test owns the geometry."""

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vectors[text] for text in texts]


async def chunk_in(
    db_session: AsyncSession,
    *,
    exam_id: uuid.UUID | None,
    corpus: str = "summary",
    source_id: str = "s1",
    title: str = "Chest pain",
    texts: Sequence[tuple[str, list[float]]],
) -> int:
    return await repository_index.replace_source(
        db_session,
        corpus=corpus,
        source_id=source_id,
        exam_id=exam_id,
        title=title,
        chunks=[
            {"index": i, "section": "management", "text": text, "embedding": embedding}
            for i, (text, embedding) in enumerate(texts)
        ],
    )


async def test_passages_come_back_nearest_first(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await chunk_in(
        db_session,
        exam_id=exam.id,
        texts=[("anxiety advice", ANXIETY), ("breathlessness advice", BREATHLESS)],
    )

    rows = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[exam.id], corpus=None, limit=5
    )

    assert [row.text for row, _ in rows] == ["breathlessness advice", "anxiety advice"]
    # Cosine distance turned into a score, so larger is better above this line.
    assert rows[0][1] > rows[1][1]


async def test_an_exam_the_learner_does_not_hold_is_filtered_out(db_session: AsyncSession) -> None:
    """The filter is the entitlement, so it has to happen in SQL, not after."""
    held = await ensure_exam(db_session, "sca")
    other = await ensure_exam(db_session, "plab")
    assert held is not None and other is not None
    await chunk_in(db_session, exam_id=other.id, source_id="locked", texts=[("chest pain", CHEST_PAIN)])
    await chunk_in(db_session, exam_id=held.id, source_id="open", texts=[("anxiety", ANXIETY)])

    rows = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[held.id], corpus=None, limit=5
    )

    # The nearest passage in the table is the one they may not read, so a
    # post-filter would have returned nothing at all here.
    assert [row.text for row, _ in rows] == ["anxiety"]


async def test_holding_no_exam_finds_only_the_shared_help(db_session: AsyncSession) -> None:
    """No exams reaches the help every exam shares, never paid material or another exam's help."""
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await chunk_in(db_session, exam_id=exam.id, texts=[("chest pain", CHEST_PAIN)])
    await chunk_in(
        db_session, exam_id=None, corpus="help", source_id="first-steps", texts=[("start", CHEST_PAIN)]
    )
    await chunk_in(
        db_session, exam_id=exam.id, corpus="help", source_id="practice@sca", texts=[("peers", CHEST_PAIN)]
    )

    nobody = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[], corpus=None, limit=5
    )
    holder = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[exam.id], corpus=None, limit=5
    )

    assert [row.source_id for row, _ in nobody] == ["first-steps"]
    assert sorted(row.source_id for row, _ in holder) == ["first-steps", "practice@sca", "s1"]


async def test_a_corpus_can_be_narrowed(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await chunk_in(db_session, exam_id=exam.id, corpus="summary", source_id="a", texts=[("x", CHEST_PAIN)])
    await chunk_in(db_session, exam_id=exam.id, corpus="station", source_id="b", texts=[("y", CHEST_PAIN)])

    rows = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[exam.id], corpus="station", limit=5
    )

    assert [row.corpus for row, _ in rows] == ["station"]


async def test_reindexing_a_shorter_document_drops_the_passages_it_lost(
    db_session: AsyncSession,
) -> None:
    """The case an add-only index gets wrong: answering out of deleted text."""
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await chunk_in(
        db_session,
        exam_id=exam.id,
        texts=[("kept and rewritten", CHEST_PAIN), ("removed by the author", ANXIETY)],
    )

    await chunk_in(db_session, exam_id=exam.id, texts=[("rewritten", CHEST_PAIN)])

    rows = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[exam.id], corpus=None, limit=5
    )
    assert [row.text for row, _ in rows] == ["rewritten"]


async def test_unpublishing_a_source_forgets_every_passage_of_it(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await chunk_in(db_session, exam_id=exam.id, texts=[("a", CHEST_PAIN), ("b", ANXIETY)])

    removed = await repository_index.forget_source(db_session, corpus="summary", source_id="s1")

    assert removed == 2
    assert await repository_index.indexed_source_ids(db_session, corpus="summary") == set()


async def test_the_adapter_embeds_the_query_and_maps_rows_to_passages(
    db_session: AsyncSession,
) -> None:
    """The port's own contract, over the real table underneath it."""
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    embedder = ScriptedEmbedder(
        {"safety net chest pain": CHEST_PAIN, "advice about breathlessness": BREATHLESS}
    )
    index = PgVectorMaterialIndex(db_session, embedder)

    written = await index.upsert(
        corpus="summary",
        source_id="s1",
        exam_id=str(exam.id),
        title="Chest pain",
        chunks=[{"index": 0, "section": "red_flags", "text": "advice about breathlessness"}],
    )
    found = await index.search(query="safety net chest pain", exam_ids=[str(exam.id)], corpus=None, limit=3)

    assert written == 1
    assert [(p.title, p.section, p.corpus) for p in found] == [("Chest pain", "red_flags", "summary")]
    assert found[0].score > 0
    # The passage text travels with the hit: the tutor quotes and cites in one
    # breath, and a second read to resolve ids would sit in the voice loop.
    assert found[0].text == "advice about breathlessness"


async def test_an_empty_chunk_list_removes_the_source_rather_than_embedding_nothing(
    db_session: AsyncSession,
) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    embedder = ScriptedEmbedder({"a": CHEST_PAIN})
    index = PgVectorMaterialIndex(db_session, embedder)
    await index.upsert(
        corpus="summary",
        source_id="s1",
        exam_id=str(exam.id),
        title="T",
        chunks=[{"index": 0, "section": "management", "text": "a"}],
    )

    removed = await index.upsert(corpus="summary", source_id="s1", exam_id=str(exam.id), title="T", chunks=[])

    assert removed == 1
    assert len(embedder.calls) == 1
    assert await repository_index.indexed_source_ids(db_session, corpus="summary") == set()


def passage(index: int, text_: str, section: str = "management") -> dict[str, object]:
    return {"index": index, "section": section, "text": text_}


async def test_a_source_that_has_not_changed_is_not_embedded_again(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    embedder = ScriptedEmbedder({"a": CHEST_PAIN, "b": BREATHLESS})
    index = PgVectorMaterialIndex(db_session, embedder)
    source = {"corpus": "summary", "source_id": "s1", "exam_id": str(exam.id), "title": "T"}
    await index.upsert(**source, chunks=[passage(0, "a"), passage(1, "b")])

    held = await index.upsert(**source, chunks=[passage(0, "a"), passage(1, "b")])

    assert held == 2
    assert embedder.calls == [["a", "b"]]


async def test_only_the_passage_that_was_edited_is_embedded(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    embedder = ScriptedEmbedder({"a": CHEST_PAIN, "b": BREATHLESS, "c": ANXIETY})
    index = PgVectorMaterialIndex(db_session, embedder)
    source = {"corpus": "summary", "source_id": "s1", "exam_id": str(exam.id), "title": "T"}
    await index.upsert(**source, chunks=[passage(0, "a"), passage(1, "b")])

    await index.upsert(**source, chunks=[passage(0, "a"), passage(1, "c")])

    assert embedder.calls == [["a", "b"], ["c"]]
    stored = await repository_index.stored_passages(db_session, corpus="summary", source_id="s1")
    assert stored == {0: ("management", "a"), 1: ("management", "c")}
    found = await index.search(query="c", exam_ids=[str(exam.id)], corpus=None, limit=1)
    assert [p.text for p in found] == ["c"]


async def test_a_renamed_or_moved_source_keeps_its_vectors(db_session: AsyncSession) -> None:
    sca = await ensure_exam(db_session, "sca")
    plab = await ensure_exam(db_session, "plab")
    assert sca is not None and plab is not None
    embedder = ScriptedEmbedder({"a": CHEST_PAIN})
    index = PgVectorMaterialIndex(db_session, embedder)
    await index.upsert(
        corpus="summary", source_id="s1", exam_id=str(sca.id), title="Old", chunks=[passage(0, "a")]
    )

    await index.upsert(
        corpus="summary", source_id="s1", exam_id=str(plab.id), title="New", chunks=[passage(0, "a")]
    )

    assert embedder.calls == [["a"]]
    rows = (
        await db_session.execute(
            text("SELECT title, exam_id FROM material_chunks WHERE corpus = 'summary' AND source_id = 's1'")
        )
    ).all()
    assert rows == [("New", plab.id)]
    assert await index.search(query="a", exam_ids=[str(sca.id)], corpus="summary", limit=3) == []


async def test_several_sources_share_one_embedding_request(db_session: AsyncSession) -> None:
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    embedder = ScriptedEmbedder({"a": CHEST_PAIN, "b": BREATHLESS, "c": ANXIETY})
    index = PgVectorMaterialIndex(db_session, embedder)

    written = await index.upsert_many(
        [
            SourcePassages("summary", "s1", str(exam.id), "One", [passage(0, "a"), passage(1, "b")]),
            SourcePassages("blog", "b1", str(exam.id), "Two", [passage(0, "c")]),
            SourcePassages("blog", "b2", str(exam.id), "Gone", []),
        ]
    )

    assert written == 3
    assert embedder.calls == [["a", "b", "c"]]
    found = await index.search(query="c", exam_ids=[str(exam.id)], corpus=None, limit=1)
    assert [(p.title, p.text) for p in found] == [("Two", "c")]


async def test_the_exam_filter_does_not_starve_a_search_of_its_nearest_passages(
    db_session: AsyncSession,
) -> None:
    """The index walks nearest-first across every exam; the learner's own must still fill the answer."""
    mine = await ensure_exam(db_session, "sca")
    other = await ensure_exam(db_session, "plab")
    assert mine is not None and other is not None
    # Each a little different: identical vectors share one node of the graph, and it
    # takes more nodes than the walk keeps to leave the learner's own exam out of reach.
    for n in range(300):
        await chunk_in(
            db_session,
            exam_id=other.id,
            source_id=f"other-{n}",
            texts=[(f"other {n}", vector(1.0, 0.001 * n, 0.0))],
        )
    await chunk_in(
        db_session,
        exam_id=mine.id,
        source_id="mine",
        texts=[
            ("far one", ANXIETY),
            ("far two", vector(0.1, 1.0, 0.0)),
            ("far three", vector(0.2, 1.0, 0.0)),
        ],
    )

    # So few rows would be read straight through; make the planner take the index the
    # way it does on the real library, which is where the filter could starve it.
    for setting in ("enable_seqscan", "enable_bitmapscan", "enable_sort"):
        await db_session.execute(text(f"SET LOCAL {setting} = off"))

    rows = await repository_index.nearest(
        db_session, embedding=CHEST_PAIN, exam_ids=[mine.id], corpus=None, limit=3
    )

    assert [chunk.text for chunk, _distance in rows] == ["far three", "far two", "far one"]
