"""Answering a clinical question out of the material this doctor holds.

Sits inside a voice loop: the model says a holding line and waits on this, so the budget is
one embedding call plus one pgvector query -- about 350ms.

Nothing here decides whether a learner may read something: `domain.entitled_exam_ids` does,
over what `entitlements` returned, and the entitled exams are handed to the index as a SQL
filter.

Three answers, and the tutor says each one aloud with the same confidence, so they must not
be confused:

- `NOT_CONFIGURED` -- there is no index, or it failed. "I could not look that up."
- `NOTHING_IN_MATERIAL` -- it was searched and had nothing. "The reading does not say."
- passages -- answer from these and cite them.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import MaterialIndex, Passage, VectorIndex
from app.features.entitlements import service as entitlements
from app.features.tutor_memory import domain
from app.features.tutor_memory.embedder import EmbeddingFailed
from app.features.tutor_memory.media_index import build_media_index
from app.features.tutor_memory.schemas import ToolResult

log = get_logger(__name__)

# Three is what a spoken answer can carry. A fourth passage is not read out --
# it lengthens the prompt and gives the model more to blend into one
# undifferentiated paragraph with three citations after it.
# Enough for a conversation that stays on one subject, not just a quick answer.
SEARCH_LIMIT = 5

NOT_CONFIGURED = (
    "The material search is not available in this deployment. Say you cannot look that up "
    "right now, and answer from what you already know or offer to come back to it."
)

NOTHING_IN_MATERIAL = (
    "The material has nothing on that. Say you could not find it in their reading rather than "
    "answering from memory, and offer to come back to it."
)

# The card envelope the frontend parses. Bumped with the shape, never with the
# contents: `frontend/src/shared/livekit-ui-guidance/contracts.ts` validates it.
CARD_SCHEMA_VERSION = 2


async def answer_question(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str,
    corpus: str | None,
    index: MaterialIndex | None,
    now: datetime,
) -> ToolResult:
    """Answer a clinical question out of the material this doctor holds.

    The entitlement is worked out here and handed to the index as a filter, so a doctor is
    never ranked against material they have not bought.
    """
    if index is None:
        return ToolResult(result=NOT_CONFIGURED)

    grants = await entitlements.list_for_user(session, user_id, now=now)
    # Holding nothing still searches: the help articles every exam shares need
    # no entitlement, so an institution admin can ask how the app works.
    exam_ids = [str(exam_id) for exam_id in domain.entitled_exam_ids(grants)]

    try:
        passages = await index.search(query=query, exam_ids=exam_ids, corpus=corpus, limit=SEARCH_LIMIT)
    except EmbeddingFailed as exc:
        # The embedding API is down or refused. Not "nothing found", which
        # would have the tutor assert -- in a clinical conversation -- that the
        # reading does not cover something it never managed to read.
        log.warning("material search failed", error=str(exc))
        return ToolResult(result=NOT_CONFIGURED)

    if not passages:
        return ToolResult(result=NOTHING_IN_MATERIAL)

    slugs = await _slugs(session, passages)
    return ToolResult(result=_readable(passages, slugs), display=_citations(passages, slugs))


def _readable(passages: Sequence[Passage], slugs: dict[str, str]) -> str:
    """The passages, numbered, with the instruction to cite them as it speaks.

    Numbered markers rather than titles inline, since a title read aloud mid-sentence is a
    mouthful; the card carries the titles for the screen instead.
    """
    body = "\n\n".join(
        f"[{number}] (ref {slugs.get(passage.source_id) or passage.source_id}) {passage.text}"
        for number, passage in enumerate(passages, start=1)
    )
    return (
        "Here is what the material says. Answer from this and nothing else, in two or three "
        "spoken sentences. Refer to a source as 'the first one' or by its title, never by its "
        "number, and tell them the sources are on their screen. Never say a ref aloud; it is "
        f"only for putting one on their screen with a suggestion.\n\n{body}"
    )


def _source_id(passage: Passage) -> str:
    """The id a citation carries: a help article's slug without its exam suffix."""
    if passage.corpus == domain.HELP_CORPUS:
        return help_slug(passage.source_id)
    return passage.source_id


def help_slug(source_id: str) -> str:
    """The article slug from a help source id (`<slug>` or `<slug>@<exam code>`)."""
    return source_id.split("@", 1)[0]


async def _slugs(session: AsyncSession, passages: Sequence[Passage]) -> dict[str, str]:
    """The slug each cited source opens by: media items from `media`, help from its id.

    At most `SEARCH_LIMIT` reads, so one per item rather than a bulk call. An
    item gone since the last re-index keeps its citation, without a link.
    """
    from app.features.media import errors as media_errors  # avoids an import cycle
    from app.features.media import service as media

    slugs: dict[str, str] = {}
    for passage in passages:
        if passage.corpus == domain.HELP_CORPUS:
            slugs[passage.source_id] = help_slug(passage.source_id)
        elif passage.corpus in domain.MEDIA_KINDS and passage.source_id not in slugs:
            try:
                media_item = await media.read_by_id(
                    session, uuid.UUID(passage.source_id), viewer_is_admin=True
                )
            except (ValueError, media_errors.ItemNotFound):
                continue
            slugs[passage.source_id] = media_item.slug
    return slugs


def _citations(passages: Sequence[Passage], slugs: dict[str, str]) -> dict[str, Any]:
    """What goes on the screen beside the spoken answer.

    A ref per passage in the same spelling `suggest_material` uses, since the frontend
    resolves both through one route resolver. A help article and a media item carry the
    slug their page opens by; a station opens by its id.
    """
    return {
        "type": "assistant_card",
        "schemaVersion": CARD_SCHEMA_VERSION,
        "card": "citations",
        "citations": [
            {
                "n": number,
                "title": passage.title,
                "section": passage.section,
                "ref": {
                    "kind": passage.corpus,
                    "id": _source_id(passage),
                    "slug": slugs.get(passage.source_id),
                },
            }
            for number, passage in enumerate(passages, start=1)
        ],
    }


def media_title_index(session: AsyncSession) -> VectorIndex:
    """The index behind `media`'s search box: the same store, searched for items."""
    return build_media_index(session)
