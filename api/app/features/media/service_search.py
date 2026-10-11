"""Searching published study material, and which exams a reader may open."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionDep
from app.core.errors import AppError, InvalidInput, raise_mapped
from app.core.pagination import encode_cursor
from app.core.ports import VectorIndex
from app.features.catalog import service as catalog
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.media import domain, errors, repository
from app.features.media.schemas import SearchHit
from app.features.tutor_memory import service_search as tutor_search

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

    The index holds ids only, so what a reader sees always comes from the
    database — an item unpublished since it was indexed cannot leak through a
    stale entry.

    Scoped to what the reader holds, like the tutor's own search
    (`tutor_memory.service_search`). Free material — no exam — is searchable
    by everybody.

    Ranked best first, ties broken by id, since `search_page` cursors this list.
    """
    try:
        cleaned = domain.clean_query(query)
        wanted = domain.normalize_kind(kind) if kind else None
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    hits = await index.search(query=cleaned, limit=limit, kind=wanted)
    scores = {uuid.UUID(doc_id): score for doc_id, score in hits}
    items = await repository.by_ids(session, list(scores))
    return sorted(
        (
            SearchHit(
                id=item.id,
                kind=item.kind,
                slug=item.slug,
                title=item.title,
                score=scores.get(item.id, 0.0),
                excerpt=domain.excerpt(item.summary, item.title),
            )
            for item in items
            if domain.is_public(status=item.status)
            and (wanted is None or item.kind == wanted)
            and (item.exam_id is None or item.exam_id in unlocked)
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
    whole match, cursor aside.
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
    unlocked = {grant.exam_id for grant in grants if grant.live and grant.exam_id}
    user = await identity.user_ref_by_id(session, user_id)
    if (
        user
        and user.exam_code
        and user.created_at <= now < user.created_at + timedelta(days=_STUDY_TRIAL_DAYS)
    ):
        exams = await catalog.exam_refs(session)
        unlocked.update(exam.id for exam in exams if exam.code == user.exam_code)
    return frozenset(unlocked)


def get_vector_index(session: SessionDep) -> VectorIndex:
    """The dependency the router wires. Overridden in tests with a fake.

    The pgvector store the tutor reads (ADR 0019), owned by `tutor_memory`.
    Takes the request's session because indexing on publish belongs in the
    same transaction that published.

    **Entitlement is deliberately not applied.** This searches *titles*, and
    `GET /api/v1/media` already lists every published item to any signed-in
    reader, so filtering search and not the list would mean an item you can
    see in one place and not find in the other. Opening an item still goes
    through `read_by_slug`, which decides access to the content.
    """
    return tutor_search.media_title_index(session)
