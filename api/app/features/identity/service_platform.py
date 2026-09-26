"""Accounts as the platform console sees them.

Every caller is behind `PlatformAdmin`. Rows never leave the slice: `SupportUser` carries
the account flags the console shows, and `UserRef` stays the small shape everything else
gets.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository, repository_platform
from app.features.identity.models import User


@dataclass(frozen=True)
class SupportUser:
    """One account, with the flags a support conversation turns on."""

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    status: str
    is_platform_admin: bool
    must_change_password: bool
    last_login_at: datetime | None
    exam_code: str | None
    exam_date: date | None = None
    extra_reading_percent: int = 0
    consumer_role: str = "user"


def _support(user: User) -> SupportUser:
    return SupportUser(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        status=user.status,
        is_platform_admin=user.is_platform_admin,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        exam_code=user.exam_code,
        exam_date=user.exam_date,
        extra_reading_percent=user.extra_reading_percent,
        consumer_role=user.consumer_role,
    )


async def search_users(
    session: AsyncSession,
    *,
    query: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    platform_admin: bool | None = None,
    status: str | None = None,
    exam_code: str | None = None,
    exam_user_ids: Collection[uuid.UUID] | None = None,
    only_ids: Collection[uuid.UUID] | None = None,
    except_ids: Collection[uuid.UUID] | None = None,
    no_exam: bool = False,
) -> tuple[list[SupportUser], str | None]:
    """Find people by a fragment of their email or name.

    The one read in the API that crosses every tenant at once, which is why
    only the console reaches it. `platform_admin=True` narrows it to the
    people who may use that console.

    The directory's other facets — who has paid, who has attempted anything,
    who holds a live grant — are other slices' facts, and this slice cannot
    read their tables. They arrive as sets of ids: `exam_user_ids` widens an
    `exam_code` match to the people entitled to that exam, `only_ids` and
    `except_ids` narrow to or away from a set the caller computed, and
    `no_exam` is the accounts that chose none.
    """
    users, next_cursor = await repository_platform.search_users(
        session,
        query=query,
        limit=limit,
        cursor=cursor,
        platform_admin=platform_admin,
        status=status,
        exam_code=exam_code,
        exam_user_ids=exam_user_ids,
        only_ids=only_ids,
        except_ids=except_ids,
        no_exam=no_exam,
    )
    return [_support(user) for user in users], next_cursor


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
    """How many accounts `search_users` would page through with these facets."""
    return await repository_platform.count_users_matching(
        session,
        status=status,
        exam_code=exam_code,
        exam_user_ids=exam_user_ids,
        only_ids=only_ids,
        except_ids=except_ids,
        no_exam=no_exam,
    )


async def signed_in_user_ids(
    session: AsyncSession, user_ids: Collection[uuid.UUID], *, now: datetime
) -> set[uuid.UUID]:
    """Which of these people hold a sign-in that has neither expired nor been
    revoked — the nearest thing to the old console's Online column."""
    return await repository_platform.signed_in_user_ids(session, list(user_ids), now=now)


async def user_by_id(session: AsyncSession, user_id: uuid.UUID) -> SupportUser | None:
    user = await repository.user_by_id(session, user_id)
    return None if user is None else _support(user)


async def list_platform_admins(session: AsyncSession, *, limit: int) -> list[SupportUser]:
    return [_support(user) for user in await repository_platform.list_platform_admins(session, limit=limit)]


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str | None = None,
    exam_code: str | None = None,
    status: str | None = None,
    exam_date: date | None = None,
    extra_reading_percent: int | None = None,
) -> SupportUser | None:
    """Write only what the console sent; `None` means "leave it"."""
    if await repository.user_by_id(session, user_id) is None:
        return None
    sent = {
        "name": name,
        "exam_code": exam_code,
        "status": status,
        "exam_date": exam_date,
        "extra_reading_percent": extra_reading_percent,
    }
    changes = {field: value for field, value in sent.items() if value is not None}
    await repository_platform.update_admin_fields(session, user_id, **changes)
    return await user_by_id(session, user_id)


async def consumer_legacy_ids(session: AsyncSession, user_id: uuid.UUID) -> dict[str, str]:
    """Legacy consumer subject ids keyed by exam, for the staff console."""
    return await repository.consumer_legacy_ids(session, user_id)
