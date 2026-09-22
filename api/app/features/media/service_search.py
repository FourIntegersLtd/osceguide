"""Searching published study material, and which exams a reader may open."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError, raise_mapped
from app.core.ports import VectorIndex
from app.features.catalog import service as catalog
from app.features.entitlements import service as entitlements
from app.features.identity import service as identity
from app.features.media import domain, errors, repository
from app.features.media.schemas import SearchHit

# How long a new account's exam-code preference grants study access.
# Mirrors the entitlements slice's own trial window.
_STUDY_TRIAL_DAYS = 14

_REFUSALS: dict[type[Exception], type[AppError]] = {
    domain.EmptyQuery: errors.EmptyQueryError,
    domain.QueryTooLong: errors.EmptyQueryError,
}


async def search(
    session: AsyncSession,
    *,
    query: str,
    index: VectorIndex,
    limit: int = 10,
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
    """
    try:
        cleaned = domain.clean_query(query)
    except Exception as exc:  # noqa: BLE001 - mapped above
        raise_mapped(exc, _REFUSALS)

    hits = await index.search(query=cleaned, limit=limit)
    scores = {uuid.UUID(doc_id): score for doc_id, score in hits}
    rows = await repository.by_ids(session, list(scores))
    return sorted(
        (
            SearchHit(id=r.id, kind=r.kind, slug=r.slug, title=r.title, score=scores.get(r.id, 0.0))
            for r in rows
            if domain.is_public(status=r.status) and (r.exam_id is None or r.exam_id in unlocked)
        ),
        key=lambda hit: hit.score,
        reverse=True,
    )


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
