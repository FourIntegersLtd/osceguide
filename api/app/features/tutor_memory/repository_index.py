"""Storage for the material index: the passages, and the nearest-neighbour read.

Apart from `repository.py` because this table is a different kind of thing.
The others hold what one learner did and said, are written a row at a time as
it happens, and are read by user id. This one holds a rebuildable copy of the
catalogue, is written in bulk by a job, and is read by distance.

The distance operator is written out rather than reached through a helper, so
the one query that decides what the tutor quotes is readable here in full.
`<=>` is cosine distance: smaller is nearer, and a score is `1 - distance` so
that larger is better everywhere above this line.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Float, String, bindparam, cast, delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tutor_memory.models import MaterialChunk
from app.features.tutor_memory.vector_column import VECTOR, to_literal


async def replace_source(
    session: AsyncSession,
    *,
    corpus: str,
    source_id: str,
    exam_id: uuid.UUID | None,
    title: str,
    chunks: Sequence[Mapping[str, Any]],
) -> int:
    """Make the stored passages of one source exactly `chunks`.

    Upsert on `(corpus, source_id, chunk_index)` and then delete anything past
    the new end, rather than delete-then-insert. A source is re-indexed while
    the tutor may be searching, and a window in which a document has no
    passages at all is a window in which it cannot be found — so a row is
    overwritten in place and only a document that genuinely shrank loses rows.
    """
    for chunk in chunks:
        stmt = insert(MaterialChunk).values(
            corpus=corpus,
            source_id=source_id,
            exam_id=exam_id,
            title=title,
            section=str(chunk["section"]),
            chunk_index=int(chunk["index"]),
            text=str(chunk["text"]),
            embedding=list(chunk["embedding"]),
        )
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
            )
        )

    await session.execute(
        delete(MaterialChunk).where(
            MaterialChunk.corpus == corpus,
            MaterialChunk.source_id == source_id,
            MaterialChunk.chunk_index >= len(chunks),
        )
    )
    return len(chunks)


async def forget_source(session: AsyncSession, *, corpus: str, source_id: str) -> int:
    """Drop every passage of one source — what unpublishing it means here."""
    result = await session.execute(
        delete(MaterialChunk).where(MaterialChunk.corpus == corpus, MaterialChunk.source_id == source_id)
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def indexed_source_ids(session: AsyncSession, *, corpus: str) -> set[str]:
    """Which sources of a corpus have passages, so a re-index can retire the rest."""
    stmt = select(MaterialChunk.source_id).where(MaterialChunk.corpus == corpus).distinct()
    return {str(row) for row in (await session.execute(stmt)).scalars().all()}


async def nearest(
    session: AsyncSession,
    *,
    embedding: Sequence[float],
    exam_ids: Sequence[uuid.UUID] | None,
    corpus: str | None,
    limit: int,
) -> list[tuple[MaterialChunk, float]]:
    """The nearest passages, best first, within the exams given.

    The exam filter is a `WHERE`, applied before the ordering, so a doctor can
    never be ranked against material they do not hold — a post-filter would
    have thrown away the best passages and returned worse ones from the right
    exam, or nothing at all.

    Three states, and the difference between the last two is load-bearing:

    - a non-empty sequence filters to those exams;
    - **an empty sequence returns nothing**, because a caller who computed an
      empty entitled set has just decided this person may read nothing;
    - **`None` applies no filter at all**, which only the media search box
      passes. It searches titles of material `GET /media` already lists to
      every signed-in reader, so filtering it and not the list would hide in
      search what is visible in the index.

    `None` rather than a second unfiltered query, so skipping the filter is
    something a caller has to ask for by name and cannot reach by passing an
    empty list it did not notice was empty.
    """
    if exam_ids is not None and not exam_ids:
        return []

    # Bound as text and cast, because `<=>` has no `(vector, text)` form and
    # a bare string parameter would reach Postgres as one. The cast is what
    # turns `'[0.1,0.2]'` into a vector the operator class can use, which is
    # also what keeps the IVFFlat index in play.
    query_vector = cast(bindparam("query_vector", to_literal(embedding), type_=String), VECTOR())
    # `result_type` because an operator inherits its left operand's type by
    # default, and the distance would then come back through the vector
    # column's own result handling — a list of floats where a number belongs.
    distance = MaterialChunk.embedding.op("<=>", return_type=Float)(query_vector)
    stmt = select(MaterialChunk, distance.label("distance")).order_by(distance).limit(limit)
    if exam_ids is not None:
        stmt = stmt.where(MaterialChunk.exam_id.in_(list(exam_ids)))
    if corpus is not None:
        stmt = stmt.where(MaterialChunk.corpus == corpus)

    rows = (await session.execute(stmt)).all()
    return [(row[0], 1.0 - float(row[1])) for row in rows]
