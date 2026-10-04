"""Storage for the material index: the passages, and the nearest-neighbour read.

`<=>` is cosine distance: smaller is nearer, and a score is `1 - distance` so that larger is
better everywhere above this line.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Float, String, bindparam, cast, delete, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory.domain import HELP_CORPUS
from app.features.tutor_memory.models import MaterialChunk
from app.features.tutor_memory.vector_column import VECTOR, to_literal


async def stored_passages(
    session: AsyncSession, *, corpus: str, source_id: str
) -> dict[int, tuple[str, str]]:
    """What one source has indexed already: `(section, text)` by passage number.

    Read without the vectors, which is the point: a re-index compares this against the
    freshly cut passages and embeds only the ones that differ.
    """
    stmt = select(MaterialChunk.chunk_index, MaterialChunk.section, MaterialChunk.text).where(
        MaterialChunk.corpus == corpus, MaterialChunk.source_id == source_id
    )
    return {
        int(chunk_index): (str(section), str(passage))
        for chunk_index, section, passage in (await session.execute(stmt)).all()
    }


async def replace_source(
    session: AsyncSession,
    *,
    corpus: str,
    source_id: str,
    exam_id: uuid.UUID | None,
    title: str,
    chunks: Sequence[Mapping[str, Any]],
    passages: int | None = None,
) -> int:
    """Make the stored passages of one source exactly its current ones.

    `chunks` are the passages to write, each with its embedding. `passages` is how many
    the source has in all, when that is more than `chunks`: the rest are already stored
    with the right text and keep their vectors, and only take the new title and exam.

    Upsert on `(corpus, source_id, chunk_index)` and then delete anything past the new end,
    rather than delete-then-insert, so a source being re-indexed while the tutor may be
    searching is never briefly unfindable.
    """
    total = len(chunks) if passages is None else passages
    if chunks:
        stmt = insert(MaterialChunk)
        # One statement for the source's passages rather than one each.
        await session.execute(
            stmt.on_conflict_do_update(
                constraint="uq_material_chunks_passage",
                set_={
                    "exam_id": stmt.excluded.exam_id,
                    "title": stmt.excluded.title,
                    "section": stmt.excluded.section,
                    "text": stmt.excluded.text,
                    "embedding": stmt.excluded.embedding,
                    "indexed_at": text("now()"),
                },
            ),
            [
                {
                    "corpus": corpus,
                    "source_id": source_id,
                    "exam_id": exam_id,
                    "title": title,
                    "section": str(chunk["section"]),
                    "chunk_index": int(chunk["index"]),
                    "text": str(chunk["text"]),
                    "embedding": list(chunk["embedding"]),
                }
                for chunk in chunks
            ],
        )

    if total > len(chunks):
        # A renamed source, or one moved to another exam, with its text untouched: the
        # citation and the entitlement filter read these two columns, not the vector.
        await session.execute(
            update(MaterialChunk)
            .where(
                MaterialChunk.corpus == corpus,
                MaterialChunk.source_id == source_id,
                or_(MaterialChunk.title != title, MaterialChunk.exam_id.is_distinct_from(exam_id)),
            )
            .values(title=title, exam_id=exam_id)
        )

    await session.execute(
        delete(MaterialChunk).where(
            MaterialChunk.corpus == corpus,
            MaterialChunk.source_id == source_id,
            MaterialChunk.chunk_index >= total,
        )
    )
    return total


async def forget_source(session: AsyncSession, *, corpus: str, source_id: str) -> int:
    """Drop every passage of one source — what unpublishing it means here."""
    result = await session.execute(
        delete(MaterialChunk).where(MaterialChunk.corpus == corpus, MaterialChunk.source_id == source_id)
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def indexed_source_ids(session: AsyncSession, *, corpus: str) -> set[str]:
    """Which sources of a corpus have passages, so a re-index can retire the rest."""
    stmt = select(MaterialChunk.source_id).where(MaterialChunk.corpus == corpus).distinct()
    return {str(source_id) for source_id in (await session.execute(stmt)).scalars().all()}


async def nearest(
    session: AsyncSession,
    *,
    embedding: Sequence[float],
    exam_ids: Sequence[uuid.UUID] | None,
    corpus: str | tuple[str, ...] | None,
    limit: int,
) -> list[tuple[MaterialChunk, float]]:
    """The nearest passages, best first, within the exams given.

    The exam filter is a `WHERE`, applied before the ordering, so a doctor can never be
    ranked against material they do not hold.

    Three states for `exam_ids`, and the difference between the last two is load-bearing:

    - a non-empty sequence filters to those exams, plus the help articles every exam shares;
    - **an empty sequence reaches the shared help articles only** — an empty entitled set
      means this person may read none of the paid material, but may still ask how the app
      works;
    - **`None` applies no filter at all**, which only the media search box passes, since it
      searches titles `GET /media` already lists to every signed-in reader.
    """

    # Bound as text and cast, because `<=>` has no `(vector, text)` form and
    # a bare string parameter would reach Postgres as one. The cast is what
    # turns `'[0.1,0.2]'` into a vector the operator class can use, which is
    # also what keeps the HNSW index in play.
    query_vector = cast(bindparam("query_vector", to_literal(embedding), type_=String), VECTOR())
    # `result_type` because an operator inherits its left operand's type by
    # default, and the distance would then come back through the vector
    # column's own result handling — a list of floats where a number belongs.
    distance = MaterialChunk.embedding.op("<=>", return_type=Float)(query_vector)
    stmt = select(MaterialChunk, distance.label("distance")).order_by(distance).limit(limit)
    if exam_ids is not None:
        # An exam-specific help article carries its exam and is caught by the
        # first arm; one for every exam carries none and only the second finds it.
        stmt = stmt.where(
            or_(
                MaterialChunk.exam_id.in_(list(exam_ids)),
                (MaterialChunk.corpus == HELP_CORPUS) & MaterialChunk.exam_id.is_(None),
            )
        )
    if isinstance(corpus, str):
        stmt = stmt.where(MaterialChunk.corpus == corpus)
    elif corpus is not None:
        stmt = stmt.where(MaterialChunk.corpus.in_(corpus))

    # HNSW keeps `ef_search` candidates as it walks the graph, and the exam filter is
    # applied to what the walk returns. Two hundred is five times the default, for recall
    # close to an exact scan. `strict_order` lets the walk carry on when the filter has
    # thrown most of them away, so a doctor holding one small exam still gets `limit`
    # passages, in exact distance order. `true` scopes both to this transaction.
    await session.execute(
        text(
            "SELECT set_config('hnsw.ef_search', '200', true), "
            "set_config('hnsw.iterative_scan', 'strict_order', true)"
        )
    )
    matches = (await session.execute(stmt)).all()
    if len(matches) < limit:
        # The walk is approximate and can still come back short of what the filter allows.
        # Ordering by an expression the index cannot serve reads every allowed row
        # instead, which is exact, and at a library's size costs a few milliseconds.
        exact = stmt.order_by(None).order_by(distance + 0)
        matches = (await session.execute(exact)).all()
    return [(match[0], 1.0 - float(match[1])) for match in matches]
