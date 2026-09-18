"""Answering a clinical question out of the material this doctor holds.

Sits inside a voice loop: the model says a holding line and waits on this, so
the budget is one embedding call plus one pgvector query -- about 350ms -- and
anything slower is heard as a pause in a conversation.

Nothing here decides whether a learner may read something. It works out the
entitled exams and hands them to the index, which filters in SQL. The decision
itself is `domain.entitled_exam_ids` over what `entitlements` returned, so it
can be tested without an index at all and cannot be quietly skipped.

Three answers, and the difference between them matters because the tutor says
each one aloud with the same confidence:

- `NOT_CONFIGURED` -- there is no index, or it failed. "I could not look that up."
- `NOTHING_IN_MATERIAL` -- it was searched and had nothing. "The reading does not say."
- passages -- answer from these and cite them.

Returning the second where the first is true would have the tutor assert, in a
clinical conversation, that the reading does not cover something it never read.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.ports import MaterialIndex, Passage
from app.features.entitlements import service as entitlements
from app.features.tutor_memory import domain
from app.features.tutor_memory.embedder import EmbeddingFailed
from app.features.tutor_memory.schemas import ToolResult

log = get_logger(__name__)

# Three is what a spoken answer can carry. A fourth passage is not read out --
# it lengthens the prompt and gives the model more to blend into one
# undifferentiated paragraph with three citations after it.
SEARCH_LIMIT = 3

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

    The entitlement is worked out here and handed to the index as a filter, so
    a doctor is never ranked against material they have not bought. Today the
    A to Z and the slides are gated in the browser only — a tutor that read out
    of them would be a way round that, and the gate is a `WHERE` clause now.
    """
    if index is None:
        return ToolResult(result=NOT_CONFIGURED)

    grants = await entitlements.list_for_user(session, user_id, now=now)
    exam_ids = [str(exam_id) for exam_id in domain.entitled_exam_ids(grants)]
    if not exam_ids:
        # Holding nothing is not an error and not "nothing found": there is
        # simply no material this person may be read out of.
        return ToolResult(result=NOTHING_IN_MATERIAL)

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

    return ToolResult(result=_readable(passages), display=_citations(passages))


def _readable(passages: Sequence[Passage]) -> str:
    """The passages, numbered, with the instruction to cite them as it speaks.

    Numbered markers rather than titles inline: the tutor is speaking, and a
    title read aloud mid-sentence is a mouthful. The card carries the titles
    for the screen, and the model is told to say "I have put the sources on
    your screen" rather than to read them out.
    """
    body = "\n\n".join(f"[{n}] {p.text}" for n, p in enumerate(passages, start=1))
    return (
        "Here is what the material says. Answer from this and nothing else, in two or three "
        "spoken sentences. Refer to a source as 'the first one' or by its title, never by its "
        f"number, and tell them the sources are on their screen.\n\n{body}"
    )


def _citations(passages: Sequence[Passage]) -> dict[str, Any]:
    """What goes on the screen beside the spoken answer.

    A ref per passage in the same spelling `suggest_material` uses, because the
    frontend resolves both through one route resolver — the tutor cites and
    suggests the same things, and two spellings for one identifier is one too
    many.
    """
    return {
        "type": "assistant_card",
        "schemaVersion": CARD_SCHEMA_VERSION,
        "card": "citations",
        "citations": [
            {
                "n": n,
                "title": p.title,
                "section": p.section,
                "ref": {"kind": p.corpus, "id": p.source_id, "slug": None},
            }
            for n, p in enumerate(passages, start=1)
        ],
    }
