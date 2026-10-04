"""Answering a clinical question out of the material this doctor holds.

Sits inside a voice loop: the model says a holding line and waits on this, so the budget is
one embedding call plus one pgvector query -- about 350ms.

Nothing here decides whether a learner may read something: `domain.entitled_exam_ids` does,
over what `entitlements` returned, and the entitled exams are handed to the index as a SQL
filter.

Our own material is the first line. The clinical guideline library is asked at the same
time, not afterwards, so being the second line costs the doctor no extra wait; it is given a
fixed time to answer and is left out when it takes longer.

Three answers, and the tutor says each one aloud with the same confidence, so they must not
be confused:

- `NOT_CONFIGURED` -- there is no index, or it failed. "I could not look that up."
- `NOTHING_IN_MATERIAL` -- both were searched and had nothing. "The reading does not say."
- passages -- answer from these and cite them, the material before the guidelines.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import GuidelineIndex, GuidelinePassage, MaterialIndex, Passage, VectorIndex
from app.features.entitlements import service as entitlements
from app.features.tutor_memory import domain
from app.features.tutor_memory.embedder import EmbeddingFailed as EmbeddingFailed
from app.features.tutor_memory.guidelines import build_guideline_index
from app.features.tutor_memory.index import build_material_index
from app.features.tutor_memory.media_index import build_media_index
from app.features.tutor_memory.schemas import ToolResult

log = get_logger(__name__)

# Three is what a spoken answer can carry. A fourth passage is not read out --
# it lengthens the prompt and gives the model more to blend into one
# undifferentiated paragraph with three citations after it.
# Enough for a conversation that stays on one subject, not just a quick answer.
SEARCH_LIMIT = 5

# Guidelines sit behind the material, so fewer of them, and never reranked here: the
# reranker alone takes longer than the whole lookup is allowed.
GUIDELINE_LIMIT = 3
GUIDELINE_TIMEOUT_SECONDS = 1.5
GUIDELINE_PASSAGE_CHARS = 1500

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
    guidelines: GuidelineIndex | None = None,
) -> ToolResult:
    """Answer a clinical question out of the material this doctor holds, then the guidelines.

    The entitlement is worked out here and handed to the index as a filter, so a doctor is
    never ranked against material they have not bought.
    """
    # Side by side, so the second line adds nothing to the wait. A question about how
    # the app works is not one a clinical guideline answers.
    wants_guidelines = guidelines is not None and corpus != domain.HELP_CORPUS
    (passages, searched), found = await asyncio.gather(
        _material(session, index, user_id=user_id, query=query, corpus=corpus, now=now),
        _guidelines(guidelines if wants_guidelines else None, query),
    )
    if not passages and not found:
        return ToolResult(result=NOTHING_IN_MATERIAL if searched else NOT_CONFIGURED)

    slugs = await _slugs(session, passages)
    return ToolResult(
        result=_readable(passages, slugs, found),
        display=_citations(passages, slugs) if passages else None,
    )


async def _material(
    session: AsyncSession,
    index: MaterialIndex | None,
    *,
    user_id: uuid.UUID,
    query: str,
    corpus: str | None,
    now: datetime,
) -> tuple[list[Passage], bool]:
    """The passages this doctor holds, and whether the material was searched at all."""
    if index is None:
        return [], False
    grants = await entitlements.list_for_user(session, user_id, now=now)
    # Holding nothing still searches: the help articles every exam shares need
    # no entitlement, so an institution admin can ask how the app works.
    exam_ids = [str(exam_id) for exam_id in domain.entitled_exam_ids(grants)]
    try:
        return await index.search(query=query, exam_ids=exam_ids, corpus=corpus, limit=SEARCH_LIMIT), True
    except EmbeddingFailed as exc:
        # The embedding API is down or refused. Not "nothing found", which
        # would have the tutor assert -- in a clinical conversation -- that the
        # reading does not cover something it never managed to read.
        log.warning("material search failed", error=str(exc))
        return [], False


async def _guidelines(guidelines: GuidelineIndex | None, query: str) -> list[GuidelinePassage]:
    """What the guideline library has, within the time a spoken answer can spare."""
    if guidelines is None:
        return []
    try:
        return await asyncio.wait_for(
            guidelines.search(query=query, limit=GUIDELINE_LIMIT, rerank=True),
            timeout=GUIDELINE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        log.info("guideline search left out", reason="slower than the voice loop allows")
        return []


def _readable(
    passages: Sequence[Passage], slugs: dict[str, str], guidelines: Sequence[GuidelinePassage] = ()
) -> str:
    """The passages, numbered, with the instruction to cite them as it speaks.

    Numbered markers rather than titles inline, since a title read aloud mid-sentence is a
    mouthful; the card carries the titles for the screen instead. Guidelines follow, marked
    as the second line, and are not on the card: there is no page of ours to open them by.
    """
    parts: list[str] = []
    if passages:
        body = "\n\n".join(
            f"[{number}] (ref {slugs.get(passage.source_id) or passage.source_id}) {passage.text}"
            for number, passage in enumerate(passages, start=1)
        )
        parts.append(
            "Here is what the material says. Answer from this first, in two or three "
            "spoken sentences. Refer to a source as 'the first one' or by its title, never by its "
            "number, and tell them the sources are on their screen. Never say a ref aloud; it is "
            f"only for putting one on their screen with a suggestion.\n\n{body}"
        )
    if guidelines:
        body = "\n\n".join(
            f"[{passage.source}] {passage.text[:GUIDELINE_PASSAGE_CHARS]}" for passage in guidelines
        )
        lead = (
            "Clinical guidelines, the second line. Use these only for what the material above does not cover."
            if passages
            else "Their own material has nothing on that, so say so first. These clinical guidelines do."
        )
        parts.append(
            f"{lead} Say that it comes from the guideline and name it; these are not on their "
            f"screen. Answer from this and nothing else.\n\n{body}"
        )
    return "\n\n".join(parts)


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


def material_index(session: AsyncSession) -> MaterialIndex | None:
    """The passage index for another slice's request, or `None` where nothing can embed."""
    return build_material_index(session)


def guideline_index() -> GuidelineIndex | None:
    """The clinical guideline library, or `None` where this deployment has no key for it."""
    return build_guideline_index()
