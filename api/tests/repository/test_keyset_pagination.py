"""Paging must not lose rows that share a timestamp.

`created_at` is the transaction's `now()`, so everything inserted together
shares it to the microsecond. A cursor on the timestamp alone skipped every
row sharing the boundary row's timestamp; ten repositories had that bug.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import decode_cursor, keyset_page
from app.features.identity import repository as identity_repo
from app.features.identity.models import User

pytestmark = pytest.mark.db


async def _users(session: AsyncSession, n: int) -> set[uuid.UUID]:
    tag = uuid.uuid4().hex[:6]
    ids = set()
    for i in range(n):
        user = await identity_repo.create_user(
            session, email=f"page-{tag}-{i}@example.com", name="P", password_hash=None
        )
        ids.add(user.id)
    await session.flush()
    return ids


async def _walk(
    session: AsyncSession, ids: set[uuid.UUID], *, limit: int, descending: bool
) -> list[uuid.UUID]:
    seen: list[uuid.UUID] = []
    cursor: str | None = None
    while True:
        page, cursor = await keyset_page(
            session,
            select(User).where(User.id.in_(ids)),
            sort_col=User.created_at,
            id_col=User.id,
            limit=limit,
            cursor=decode_cursor(cursor) if cursor else None,
            descending=descending,
        )
        seen.extend(u.id for u in page)
        if cursor is None:
            return seen


@pytest.mark.parametrize("descending", [True, False])
async def test_rows_sharing_a_timestamp_are_all_paged_exactly_once(
    db_session: AsyncSession, descending: bool
) -> None:
    ids = await _users(db_session, 7)  # one transaction: seven identical created_at values
    walked = await _walk(db_session, ids, limit=3, descending=descending)
    assert len(walked) == 7, "a row sharing the boundary timestamp was skipped or repeated"
    assert set(walked) == ids


async def test_a_page_smaller_than_the_limit_has_no_next_cursor(db_session: AsyncSession) -> None:
    ids = await _users(db_session, 2)
    page, next_cursor = await keyset_page(
        db_session,
        select(User).where(User.id.in_(ids)),
        sort_col=User.created_at,
        id_col=User.id,
        limit=5,
        cursor=None,
    )
    assert len(page) == 2
    assert next_cursor is None
