"""Ports for finding the right passage of study material.

Split from `ports_models.py`, which is every port that *speaks* to a model.
These are the ports that *search*: embedding is here rather than there because
nothing embeds for its own sake — a vector exists to be compared with another
one, and the two halves are useless apart.

Kept out of `ports.py` for the same reason that file's model-facing half moved
out: three files each read at a different time beat one nobody reads. Every
one is re-exported from `ports.py`, so callers still have one import for "a
port".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Turns text into vectors, for searching study material by meaning.

    Declared now and used when the material index lands: the tutor's
    `search_material` tool answers "not configured" until then, and a port that
    arrives with its first caller tends to be shaped by that one caller.
    """

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in the order given."""
        ...


@dataclass(frozen=True)
class Passage:
    """One retrieved piece of study material, with enough to cite it.

    Carries the text rather than an id to look up, because the tutor speaks the
    answer and the citation in the same breath: a second read to turn three ids
    into three titles would put a database round trip inside the voice loop.

    `ref` is what the frontend resolves to a screen, in the spelling
    `suggest_material` already uses — the tutor cites and suggests the same
    things, and two spellings for one identifier is one too many.
    """

    corpus: str
    source_id: str
    title: str
    text: str
    section: str
    score: float


@runtime_checkable
class MaterialIndex(Protocol):
    """Semantic search over the study material, filtered by what a learner holds.

    Distinct from `ports.VectorIndex`, which searches whole media items by id
    for the media slice's own search box. This one retrieves *passages* — a
    question about safety-netting chest pain is answered by two paragraphs of
    one station's management plan, not by the station — and it filters by exam,
    because a doctor must not be read an answer out of material they have not
    bought.

    The exam filter is a parameter rather than something the adapter works out,
    so the entitlement decision stays in the slice where it can be tested
    without an index at all.
    """

    async def upsert(
        self,
        *,
        corpus: str,
        source_id: str,
        exam_id: str | None,
        title: str,
        chunks: Sequence[Mapping[str, Any]],
    ) -> int:
        """Replace everything held for `(corpus, source_id)` with `chunks`.

        Replace rather than add: re-indexing an edited summary that lost a
        section must lose that section from the index too, and an adapter that
        only ever adds would keep answering out of text nobody can read any
        more. Returns how many chunks the source now has.
        """
        ...

    async def search(
        self,
        *,
        query: str,
        exam_ids: Sequence[str],
        corpus: str | None,
        limit: int,
    ) -> list[Passage]:
        """Best passages first. An empty `exam_ids` returns nothing.

        Empty means "holds no exam", never "no filter": the caller passes the
        entitled set, and a caller who computed an empty one has just decided
        this person may read nothing.
        """
        ...

    async def indexed_sources(self, *, corpus: str) -> set[str]:
        """Which sources of a corpus the index holds anything for.

        Part of the port rather than something the caller reads out of its own
        storage, because retiring withdrawn material is the index's own
        business and has to be expressible against a fake. A re-index that
        asked the database directly would leave this path untested everywhere
        above the adapter — which is how twenty domain rules once passed their
        tests with no caller at all.
        """
        ...

    async def forget(self, *, corpus: str, source_id: str) -> int:
        """Drop every passage of one source. Returns how many went.

        What unpublishing means here. The failure it prevents is the quiet
        one: a withdrawn summary still being quoted, with a citation to a page
        that now returns a 404.
        """
        ...
