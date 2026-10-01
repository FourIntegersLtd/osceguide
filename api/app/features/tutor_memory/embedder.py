"""The model adapter behind `core.ports.Embedder`.

`text-embedding-3-small` because the corpus is thousands of passages of
clinical prose, not millions of documents: the larger model costs five times as
much per token and the difference it makes is not visible at this size. Which
model embeds is configuration in one place, as the summariser's is.

The model is part of the stored data, not just a setting. Vectors from two
models are not comparable, so changing the model here means re-indexing
everything — the constant is the record of which model the rows were built
with, and `docs/adr/0019-pgvector-for-tutor-material.md` says so.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.logging import get_logger
from app.core.ports import Embedder
from app.core.settings import get_settings
from app.features.tutor_memory.vector_column import EMBEDDING_DIMENSIONS

log = get_logger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_TIMEOUT_SECONDS = 30

# One request per batch of this many. The API takes a list, and a re-index of
# the whole library is thousands of passages: sending them one at a time turns
# a minute into an hour.
EMBED_BATCH = 96


class EmbeddingFailed(Exception):
    """The text could not be embedded."""


class OpenAIEmbedder:
    """Vectors from OpenAI, in the order the texts were given."""

    def __init__(self, client: Any, model: str = EMBEDDING_MODEL) -> None:
        self._client = client
        self._model = model

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in `EMBED_BATCH`-sized requests to stay within the API's limits."""
        import asyncio

        wanted = list(texts)
        if not wanted:
            return []

        def _call(batch: list[str]) -> list[list[float]]:
            """One request for one batch, its vectors put back in the batch's own order."""
            response = self._client.embeddings.create(
                model=self._model, input=batch, timeout=EMBEDDING_TIMEOUT_SECONDS
            )
            # Sorted by index rather than trusted to arrive in order: the
            # response carries one, and a silently reordered batch would
            # attach every passage's vector to the passage next to it.
            return [record.embedding for record in sorted(response.data, key=lambda entry: entry.index)]

        vectors_by_text: list[list[float]] = []
        for start in range(0, len(wanted), EMBED_BATCH):
            batch = wanted[start : start + EMBED_BATCH]
            try:
                vectors = await asyncio.to_thread(_call, batch)
            except Exception as exc:  # noqa: BLE001 - every failure here is the same failure
                raise EmbeddingFailed(f"the text could not be embedded: {exc}") from exc
            if len(vectors) != len(batch):
                raise EmbeddingFailed("the embedder returned a different number of vectors")
            vectors_by_text.extend(vectors)

        for vector in vectors_by_text:
            if len(vector) != EMBEDDING_DIMENSIONS:
                raise EmbeddingFailed(
                    f"the embedder returned {len(vector)} dimensions, and the column holds "
                    f"{EMBEDDING_DIMENSIONS}"
                )
        return vectors_by_text


def build_embedder() -> Embedder:
    """Wire the model client, or say plainly that it is not configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise EmbeddingFailed("No OPENAI_API_KEY, so nothing can be embedded.")
    try:
        from openai import OpenAI  # optional dependency
    except ImportError as exc:
        raise EmbeddingFailed("The openai package is not installed.") from exc
    return OpenAIEmbedder(OpenAI(api_key=settings.openai_api_key))
