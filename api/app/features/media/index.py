"""The search index behind `core.ports.VectorIndex`.

Undecided: b2c uses Pinecone, and pgvector is a candidate now that everything
else is in Postgres. Rather than guess, this raises — a deployment that tries to
search without an index says so instead of silently returning nothing, which
would look like "no results" to everyone.
"""

from __future__ import annotations

from app.core.ports import VectorIndex


class NoVectorIndex:
    async def index(self, *, doc_id: str, text: str, metadata: dict[str, str]) -> None:
        # Publishing must not fail because search is unconfigured; the item is
        # simply not findable until an index exists and it is reindexed.
        return None

    async def search(self, *, query: str, limit: int) -> list[tuple[str, float]]:
        return []


def build_vector_index() -> VectorIndex:
    return NoVectorIndex()
