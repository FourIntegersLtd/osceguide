"""Storage for what the platform console reads and writes about accounts.

Split from `repository.py` at the file cap. Nothing here is scoped to a
person or an organisation: these are the reads that cross every tenant at
once, and the only callers are behind `PlatformAdmin`.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.identity.models import User


async def search_users(
    session: AsyncSession,
    *,
    query: str | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
    platform_admin: bool | None = None,
) -> tuple[list[User], str | None]:
    """People, by a fragment of their email. For platform support only.

    Not scoped to anything, which is why the only route that reaches it is
    behind `PlatformAdmin`: this is the one place in the API that can see
    across every tenant at once.
    """
    stmt = select(User)
    if query:
        stmt = stmt.where(User.email.ilike(f"%{query.strip()}%"))
    if platform_admin is not None:
        stmt = stmt.where(User.is_platform_admin.is_(platform_admin))
    return await keyset_page(
        session, stmt, sort_col=User.created_at, id_col=User.id, limit=limit, cursor=cursor
    )


async def count_users(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(User))).scalar_one())


async def set_platform_admin(session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(is_platform_admin=is_admin))


async def list_platform_admins(session: AsyncSession, *, limit: int) -> list[User]:
    stmt = select(User).where(User.is_platform_admin.is_(True)).order_by(User.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars())


async def update_admin_fields(session: AsyncSession, user_id: uuid.UUID, **values: Any) -> None:
    """Write what the console changed. The caller decides which fields; an
    empty change is a no-op rather than an `UPDATE ... SET` with nothing in it."""
    if values:
        await session.execute(update(User).where(User.id == user_id).values(**values))
