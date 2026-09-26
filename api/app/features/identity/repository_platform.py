"""Storage for what the platform console reads and writes about accounts.

Nothing here is scoped to a person or an organisation: these are the reads that cross
every tenant at once, and the only callers are behind `PlatformAdmin`.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.identity.models import RefreshChain, User


def _facets(
    stmt: Select[Any],
    *,
    query: str | None = None,
    platform_admin: bool | None = None,
    status: str | None = None,
    exam_code: str | None = None,
    exam_user_ids: Collection[uuid.UUID] | None = None,
    only_ids: Collection[uuid.UUID] | None = None,
    except_ids: Collection[uuid.UUID] | None = None,
    no_exam: bool = False,
) -> Select[Any]:
    """The directory's filters, applied the same way to the page and the count.

    `exam_user_ids` widens an exam match: an account is on an exam because it
    chose it at sign-up **or** because it holds a live grant for it, and the
    second half is the entitlements slice's fact, handed in as ids. An empty
    `only_ids` is a real answer — nobody — rather than "no filter", which is
    what a missing one means.
    """
    if query:
        term = f"%{query.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(term), User.name.ilike(term)))
    if platform_admin is not None:
        stmt = stmt.where(User.is_platform_admin.is_(platform_admin))
    if status:
        stmt = stmt.where(User.status == status)
    if exam_code:
        on_exam = User.exam_code == exam_code
        if exam_user_ids:
            on_exam = or_(on_exam, User.id.in_(list(exam_user_ids)))
        stmt = stmt.where(on_exam)
    if no_exam:
        stmt = stmt.where(User.exam_code.is_(None))
    if only_ids is not None:
        stmt = stmt.where(User.id.in_(list(only_ids)))
    if except_ids:
        stmt = stmt.where(User.id.not_in(list(except_ids)))
    return stmt


async def search_users(
    session: AsyncSession,
    *,
    query: str | None,
    limit: int,
    cursor: dict[str, Any] | None = None,
    platform_admin: bool | None = None,
    status: str | None = None,
    exam_code: str | None = None,
    exam_user_ids: Collection[uuid.UUID] | None = None,
    only_ids: Collection[uuid.UUID] | None = None,
    except_ids: Collection[uuid.UUID] | None = None,
    no_exam: bool = False,
) -> tuple[list[User], str | None]:
    """People, by a fragment of their email or name. For platform support only.

    Not scoped to anything, which is why the only route that reaches it is
    behind `PlatformAdmin`: this is the one place in the API that can see
    across every tenant at once.
    """
    stmt = _facets(
        select(User),
        query=query,
        platform_admin=platform_admin,
        status=status,
        exam_code=exam_code,
        exam_user_ids=exam_user_ids,
        only_ids=only_ids,
        except_ids=except_ids,
        no_exam=no_exam,
    )
    return await keyset_page(
        session, stmt, sort_col=User.created_at, id_col=User.id, limit=limit, cursor=cursor
    )


async def count_users_matching(
    session: AsyncSession,
    *,
    status: str | None = None,
    exam_code: str | None = None,
    exam_user_ids: Collection[uuid.UUID] | None = None,
    only_ids: Collection[uuid.UUID] | None = None,
    except_ids: Collection[uuid.UUID] | None = None,
    no_exam: bool = False,
) -> int:
    stmt = _facets(
        select(func.count()).select_from(User),
        status=status,
        exam_code=exam_code,
        exam_user_ids=exam_user_ids,
        only_ids=only_ids,
        except_ids=except_ids,
        no_exam=no_exam,
    )
    return int((await session.execute(stmt)).scalar_one())


async def count_users(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(User))).scalar_one())


async def signed_in_user_ids(
    session: AsyncSession, user_ids: list[uuid.UUID], *, now: datetime
) -> set[uuid.UUID]:
    """Who among these holds a live sign-in: a refresh chain neither expired nor revoked."""
    if not user_ids:
        return set()
    stmt = (
        select(RefreshChain.user_id)
        .where(
            RefreshChain.user_id.in_(user_ids),
            RefreshChain.revoked_at.is_(None),
            RefreshChain.expires_at > now,
        )
        .distinct()
    )
    return set((await session.execute(stmt)).scalars())


async def set_platform_admin(session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(is_platform_admin=is_admin))


async def list_platform_admins(session: AsyncSession, *, limit: int) -> list[User]:
    stmt = select(User).where(User.is_platform_admin.is_(True)).order_by(User.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars())


async def update_admin_fields(session: AsyncSession, user_id: uuid.UUID, **fields: Any) -> None:
    """Write what the console changed. The caller decides which fields; an
    empty change is a no-op rather than an `UPDATE ... SET` with nothing in it."""
    if fields:
        await session.execute(update(User).where(User.id == user_id).values(**fields))
