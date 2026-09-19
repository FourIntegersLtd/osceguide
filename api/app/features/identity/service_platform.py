"""Accounts as the platform console sees them.

Split from `service.py`, which is what a person does with their own account;
these are what the people who answer support do with anybody's. Every caller
is behind `PlatformAdmin`, and `tenancy` — which owns the console — sits above
this slice and reaches these through the service rather than the table.

Rows never leave the slice: `SupportUser` carries the account flags the
console shows, and `UserRef` stays the small shape everything else gets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
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
    )


async def search_users(
    session: AsyncSession,
    *,
    query: str | None,
    limit: int,
    cursor: dict[str, Any] | None,
    platform_admin: bool | None = None,
) -> tuple[list[SupportUser], str | None]:
    """Find people by a fragment of their email.

    The one read in the API that crosses every tenant at once, which is why
    only the console reaches it. `platform_admin=True` narrows it to the
    people who may use that console.
    """
    rows, next_cursor = await repository_platform.search_users(
        session, query=query, limit=limit, cursor=cursor, platform_admin=platform_admin
    )
    return [_support(row) for row in rows], next_cursor


async def user_by_id(session: AsyncSession, user_id: uuid.UUID) -> SupportUser | None:
    user = await repository.user_by_id(session, user_id)
    return None if user is None else _support(user)


async def list_platform_admins(session: AsyncSession, *, limit: int) -> list[SupportUser]:
    return [_support(row) for row in await repository_platform.list_platform_admins(session, limit=limit)]


async def update_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str | None = None,
    exam_code: str | None = None,
    status: str | None = None,
) -> SupportUser | None:
    """Write only what the console sent; `None` means "leave it"."""
    if await repository.user_by_id(session, user_id) is None:
        return None
    changes = {
        k: v for k, v in {"name": name, "exam_code": exam_code, "status": status}.items() if v is not None
    }
    await repository_platform.update_admin_fields(session, user_id, **changes)
    return await user_by_id(session, user_id)
