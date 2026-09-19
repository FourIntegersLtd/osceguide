"""Storage for users and their sessions. Mapped classes do not leave this module."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import keyset_page
from app.features.identity.domain import normalize_email
from app.features.identity.models import (
    PasswordResetToken,
    RefreshChain,
    RefreshToken,
    User,
    UserIdentity,
)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    password_hash: str | None,
    is_platform_admin: bool = False,
    must_change_password: bool = False,
) -> User:
    user = User(
        email=normalize_email(email),
        name=name,
        password_hash=password_hash,
        is_platform_admin=is_platform_admin,
        must_change_password=must_change_password,
    )
    session.add(user)
    # Flushed and refreshed here so the caller gets the generated id and the
    # server-side defaults, rather than reaching into the session itself.
    await session.flush()
    await session.refresh(user)
    return user


async def user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def delete_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(delete(User).where(User.id == user_id))


async def set_password_hash(session: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(password_hash=password_hash, must_change_password=False)
    )


async def record_login(session: AsyncSession, user_id: uuid.UUID, at: datetime) -> None:
    await session.execute(update(User).where(User.id == user_id).values(last_login_at=at))


# --- external identities ---------------------------------------------------


async def link_identity(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str, subject: str, tenant_slug: str | None
) -> UserIdentity:
    identity = UserIdentity(user_id=user_id, provider=provider, subject=subject, tenant_slug=tenant_slug)
    session.add(identity)
    return identity


async def identity_by_subject(session: AsyncSession, provider: str, subject: str) -> UserIdentity | None:
    stmt = select(UserIdentity).where(UserIdentity.provider == provider, UserIdentity.subject == subject)
    return (await session.execute(stmt)).scalar_one_or_none()


# --- refresh chains --------------------------------------------------------


async def create_refresh_chain(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
) -> RefreshChain:
    chain = RefreshChain(user_id=user_id, expires_at=expires_at, user_agent=user_agent)
    session.add(chain)
    await session.flush()
    session.add(RefreshToken(chain_id=chain.id, token_hash=token_hash))
    return chain


async def refresh_token_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def refresh_chain_by_id(session: AsyncSession, chain_id: uuid.UUID) -> RefreshChain | None:
    stmt = select(RefreshChain).where(RefreshChain.id == chain_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def spend_and_issue(
    session: AsyncSession, *, token_id: uuid.UUID, chain_id: uuid.UUID, token_hash: str, at: datetime
) -> None:
    """Mark the presented token spent and add its successor, in one step."""
    await session.execute(update(RefreshToken).where(RefreshToken.id == token_id).values(used_at=at))
    session.add(RefreshToken(chain_id=chain_id, token_hash=token_hash))


async def revoke_refresh_chain(
    session: AsyncSession, *, chain_id: uuid.UUID, at: datetime, reason: str
) -> None:
    await session.execute(
        update(RefreshChain).where(RefreshChain.id == chain_id).values(revoked_at=at, revoked_reason=reason)
    )


async def revoke_all_chains_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, at: datetime, reason: str
) -> None:
    await session.execute(
        update(RefreshChain)
        .where(RefreshChain.user_id == user_id, RefreshChain.revoked_at.is_(None))
        .values(revoked_at=at, revoked_reason=reason)
    )


# --- password reset --------------------------------------------------------


async def create_reset_token(
    session: AsyncSession, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> PasswordResetToken:
    token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    return token


async def reset_token_by_hash(session: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_reset_token_used(session: AsyncSession, *, token_id: uuid.UUID, at: datetime) -> None:
    await session.execute(
        update(PasswordResetToken).where(PasswordResetToken.id == token_id).values(used_at=at)
    )


async def users_by_ids(session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> list[User]:
    """Several people in one query.

    The read models name a supervisor and a candidate per row; fetching them one
    id at a time is the N+1 those read models exist to delete.
    """
    if not user_ids:
        return []
    stmt = select(User).where(User.id.in_(list(user_ids)))
    return list((await session.execute(stmt)).scalars())


async def search_users(
    session: AsyncSession, *, query: str | None, limit: int, cursor: dict[str, Any] | None = None
) -> tuple[list[User], str | None]:
    """People, by a fragment of their email. For platform support only.

    Not scoped to anything, which is why the only route that reaches it is
    behind `PlatformAdmin`: this is the one place in the API that can see
    across every tenant at once.
    """
    stmt = select(User)
    if query:
        stmt = stmt.where(User.email.ilike(f"%{query.strip()}%"))
    return await keyset_page(
        session, stmt, sort_col=User.created_at, id_col=User.id, limit=limit, cursor=cursor
    )


async def count_users(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(User))).scalar_one())


async def set_platform_admin(session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(is_platform_admin=is_admin))


async def update_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str | None,
    exam_date: date | None,
    extra_reading_percent: int | None,
    clear_exam_date: bool,
) -> User | None:
    """Write only what was sent.

    `None` means "leave it" for every field, which is why clearing an exam date
    needs its own flag: a PATCH that cannot distinguish "not mentioned" from
    "set to nothing" makes one of the two impossible.
    """
    user = await session.get(User, user_id)
    if user is None:
        return None
    if name is not None:
        user.name = name
    if extra_reading_percent is not None:
        user.extra_reading_percent = extra_reading_percent
    if clear_exam_date:
        user.exam_date = None
    elif exam_date is not None:
        user.exam_date = exam_date
    await session.flush()
    return user
