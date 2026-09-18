"""The search index behind `core.ports.VectorIndex`.

pgvector, the same store the tutor's material index uses (ADR 0019), reached
through a seam rather than an import: the adapter belongs to `tutor_memory`,
which owns `material_chunks` and sits *above* this slice in the layer order.
`main.create_app` ties the two together, the way it already does for the edit
lock and the audience lookup.

`NoVectorIndex` stays as the unbound and unconfigured case. A deployment with
no embedding key has no index, and the search box then finds nothing —
honestly, because there is nothing indexed, rather than because the adapter
silently swallowed the query.

**Entitlement is deliberately not applied here.** The tutor filters its
retrieval by what a doctor holds, because it reads passages of material
aloud. This searches *titles*, and `GET /api/v1/media` already lists every
published item to any signed-in reader, so filtering search and not the list
would mean an item you can see in one place and cannot find in the other.
Opening an item still goes through `read_by_slug`, which is where access to
the content itself is decided.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import VectorIndex


class NoVectorIndex:
    """Indexes nothing and finds nothing, and says so rather than pretending."""

    async def index(self, *, doc_id: str, text: str, metadata: dict[str, str]) -> None:
        # Publishing must not fail because search is unconfigured; the item is
        # simply not findable until an index exists and it is reindexed.
        return None

    async def search(self, *, query: str, limit: int) -> list[tuple[str, float]]:
        return []


_builder: list[Callable[[AsyncSession], VectorIndex]] = []


def bind_vector_index(builder: Callable[[AsyncSession], VectorIndex]) -> None:
    """Tie the real adapter in. Called once, by `main.create_app`."""
    _builder.clear()
    _builder.append(builder)


def build_vector_index(session: AsyncSession) -> VectorIndex:
    """The bound adapter, holding this request's session.

    The session is a parameter because the index lives in the same database:
    indexing on publish must happen in the transaction that published, or a
    rolled-back publish leaves a findable item nobody can open.
    """
    return _builder[0](session) if _builder else NoVectorIndex()
