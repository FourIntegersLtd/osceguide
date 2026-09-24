"""Searching published study material, and which exams a reader may open."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, InvalidInput, raise_mapped
from app.core.pagination import encode_cursor
from app.core.ports import VectorIndex
from app.features.catalog import service as catalog
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.media import domain, errors, repository
from app.features.media.schemas import SearchHit

# How long a new account's exam-code preference grants study access.
# Mirrors the entitlements slice's own trial window.
_STUDY_TRIAL_DAYS = 14

# How deep the index is asked to rank. `VectorIndex.search` takes a limit and
# nothing else — no cursor of its own — so a page beyond this window does not
# exist to be fetched, and paging is keyset *within* it.
_RETRIEVAL_LIMIT = 100

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.EmptyQuery: errors.EmptyQueryError,
    domain.QueryTooLong: errors.EmptyQueryError,
    domain.UnknownMediaKind: errors.UnknownMediaKindError,
}


async def search(
    session: AsyncSession,
    *,
    query: str,
    index: VectorIndex,
    limit: int = 10,
    kind: str | None = None,
    unlocked: frozenset[uuid.UUID] = frozenset(),
) -> list[SearchHit]:
    """Search the index, then read the rows it named.

    The index holds ids and nothing else, so what a reader sees always comes
    from the database — an item unpublished since it was indexed cannot leak
    through a stale entry.

    Scoped to what the reader holds, the way the tutor's own search already is
    (`tutor_memory.service_search`): a hit names a title, and a search over
    every exam's material is a table of contents for the ones you have not
    bought. Free material — no exam — is searchable by everybody.

    Ranked best first, ties broken by id: `search_page` cursors through this
    list, and a cursor over an order two calls could disagree about skips or
    repeats whatever sits on the boundary.
    """
    try:
        cleaned = domain.clean_query(query)
        wanted = domain.normalize_kind(kind) if kind else None
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    hits = await index.search(query=cleaned, limit=limit)
    scores = {uuid.UUID(doc_id): score for doc_id, score in hits}
    rows = await repository.by_ids(session, list(scores))
    return sorted(
        (
            SearchHit(
                id=r.id,
                kind=r.kind,
                slug=r.slug,
                title=r.title,
                score=scores.get(r.id, 0.0),
                excerpt=domain.excerpt(r.summary, r.title),
            )
            for r in rows
            if domain.is_public(status=r.status)
            and (wanted is None or r.kind == wanted)
            and (r.exam_id is None or r.exam_id in unlocked)
        ),
        key=lambda hit: (hit.score, hit.id),
        reverse=True,
    )


async def search_page(
    session: AsyncSession,
    *,
    query: str,
    index: VectorIndex,
    kind: str | None = None,
    limit: int,
    cursor: dict[str, Any] | None = None,
    unlocked: frozenset[uuid.UUID] = frozenset(),
) -> tuple[list[SearchHit], str | None, int]:
    """One page of the ranked hits, what comes after it, and how many matched.

    Keyset on `(score, id)` rather than an offset into the ranked list, so a
    result that outranks something while the reader is paging cannot push a
    row they have already seen back onto the next page. The count is of the
    whole match, cursor aside: a search box says "18 found", and the page it
    is showing is not the answer to that question.
    """
    hits = await search(
        session, query=query, index=index, limit=_RETRIEVAL_LIMIT, kind=kind, unlocked=unlocked
    )
    return _keyset_slice(hits, cursor=cursor, limit=limit)


def _keyset_slice(
    hits: list[SearchHit], *, cursor: dict[str, Any] | None, limit: int
) -> tuple[list[SearchHit], str | None, int]:
    """Drop what a previous page already served, then take one page of the rest."""
    total = len(hits)
    remaining = hits
    if cursor:
        try:
            boundary = (float(cursor["s"]), uuid.UUID(cursor["i"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidInput("Invalid cursor") from exc
        # Strictly behind the boundary in the order `search` returned: the row
        # the cursor names was the last one the reader saw.
        remaining = [hit for hit in hits if (hit.score, hit.id) < boundary]
    if len(remaining) <= limit:
        return remaining, None, total
    page = remaining[:limit]
    last = page[-1]
    return page, encode_cursor({"s": last.score, "i": str(last.id)}), total


async def unlocked_exam_ids(
    session: AsyncSession, user_id: uuid.UUID | None, *, now: datetime
) -> frozenset[uuid.UUID]:
    """Live grants plus the account exam during its fourteen-day study trial.

    Study access is time-based, independent of the AI station trial quota.
    Resolve the account exam server-side; a browser preference grants no access.
    """
    if user_id is None:
        return frozenset()
    grants = await entitlements.list_for_user(session, user_id, now=now)
    unlocked = {g.exam_id for g in grants if g.live and g.exam_id}
    user = await identity.user_ref_by_id(session, user_id)
    if (
        user
        and user.exam_code
        and user.created_at <= now < user.created_at + timedelta(days=_STUDY_TRIAL_DAYS)
    ):
        exams = await catalog.exam_refs(session)
        unlocked.update(exam.id for exam in exams if exam.code == user.exam_code)
    return frozenset(unlocked)


def get_vector_index(session: Annotated[AsyncSession, Depends(get_session)]) -> VectorIndex:
    """The dependency the router wires. Overridden in tests with a fake.

    Takes the request's session because the index is in the same database:
    indexing on publish belongs in the transaction that published.
    """
    from app.features.media.index import build_vector_index  # noqa: PLC0415

    return build_vector_index(session)
