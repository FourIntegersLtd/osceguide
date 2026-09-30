"""Storage for the material index: the passages, and the nearest-neighbour read.

`<=>` is cosine distance: smaller is nearer, and a score is `1 - distance` so that larger is
better everywhere above this line.
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

    Upsert on `(corpus, source_id, chunk_index)` and then delete anything past the new end,
    rather than delete-then-insert, so a source being re-indexed while the tutor may be
    searching is never briefly unfindable.
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
    return {str(source_id) for source_id in (await session.execute(stmt)).scalars().all()}


async def nearest(
    session: AsyncSession,
    *,
    embedding: Sequence[float],
    exam_ids: Sequence[uuid.UUID] | None,
    corpus: str | None,
    limit: int,
) -> list[tuple[MaterialChunk, float]]:
    """The nearest passages, best first, within the exams given.

    The exam filter is a `WHERE`, applied before the ordering, so a doctor can never be
    ranked against material they do not hold.

    Three states for `exam_ids`, and the difference between the last two is load-bearing:

    - a non-empty sequence filters to those exams;
    - **an empty sequence returns nothing** — an empty entitled set means this person may
      read nothing;
    - **`None` applies no filter at all**, which only the media search box passes, since it
      searches titles `GET /media` already lists to every signed-in reader.
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

    matches = (await session.execute(stmt)).all()
    return [(match[0], 1.0 - float(match[1])) for match in matches]
