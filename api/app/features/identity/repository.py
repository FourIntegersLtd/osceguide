"""Storage for users and their sessions. Mapped classes do not leave this module."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    # Flushed here so the caller gets a row with its generated id, rather than
    # reaching into the session itself to make one appear.
    await session.flush()
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
