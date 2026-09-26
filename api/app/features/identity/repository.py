"""Storage for users and their sessions. Mapped classes do not leave this module."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime, time

from sqlalchemy import select, update
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
    exam_code: str | None = None,
    password_login_disabled: bool = False,
) -> User:
    """Write a new account. The caller has already checked the email is free
    and, for a password account, that the password is strong enough."""
    user = User(
        email=normalize_email(email),
        name=name,
        password_hash=password_hash,
        is_platform_admin=is_platform_admin,
        must_change_password=must_change_password,
        exam_code=exam_code,
        password_login_disabled=password_login_disabled,
    )
    session.add(user)
    # Flushed and refreshed so the caller gets the generated id and defaults.
    await session.flush()
    await session.refresh(user)
    return user


async def user_by_email(session: AsyncSession, email: str) -> User | None:
    """The account with this address, or None — normalising first, since
    the column is case-sensitive `citext` collision aside."""
    stmt = select(User).where(User.email == normalize_email(email))
    return (await session.execute(stmt)).scalar_one_or_none()


async def user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def set_password_hash(session: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
    """Store a new password hash and clear the forced-reset flag: setting one
    is what ends a temporary password's temporariness."""
    await session.execute(
        update(User).where(User.id == user_id).values(password_hash=password_hash, must_change_password=False)
    )


async def record_login(session: AsyncSession, user_id: uuid.UUID, at: datetime) -> None:
    await session.execute(update(User).where(User.id == user_id).values(last_login_at=at))


async def disable_password_login(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Written once, never cleared here: stays true even if the org's config
    later changes — the safer direction for a flag that only ever refuses."""
    await session.execute(update(User).where(User.id == user_id).values(password_login_disabled=True))


# --- external identities ---------------------------------------------------


async def link_identity(
    session: AsyncSession, *, user_id: uuid.UUID, provider: str, subject: str, tenant_slug: str | None
) -> UserIdentity:
    """Record that this external subject now speaks for this account."""
    identity = UserIdentity(user_id=user_id, provider=provider, subject=subject, tenant_slug=tenant_slug)
    session.add(identity)
    return identity


async def identity_by_subject(session: AsyncSession, provider: str, subject: str) -> UserIdentity | None:
    """Which account this provider's subject is linked to, or None if it has
    never signed in here before."""
    stmt = select(UserIdentity).where(UserIdentity.provider == provider, UserIdentity.subject == subject)
    return (await session.execute(stmt)).scalar_one_or_none()


async def consumer_legacy_ids(session: AsyncSession, user_id: uuid.UUID) -> dict[str, str]:
    """Firestore `user_id` per exam (`tenant_slug`), for the staff console."""
    stmt = select(UserIdentity.tenant_slug, UserIdentity.subject).where(
        UserIdentity.user_id == user_id,
        UserIdentity.provider == "consumer",
    )
    legacy_ids_by_exam: dict[str, str] = {}
    for slug, subject in (await session.execute(stmt)).all():
        key = str(slug or "unknown").lower()
        legacy_ids_by_exam[key] = str(subject)
    return legacy_ids_by_exam


# --- refresh chains --------------------------------------------------------


async def create_refresh_chain(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
) -> RefreshChain:
    """Start a new sign-in: a chain and its first token, ready to rotate."""
    chain = RefreshChain(user_id=user_id, expires_at=expires_at, user_agent=user_agent)
    session.add(chain)
    await session.flush()
    session.add(RefreshToken(chain_id=chain.id, token_hash=token_hash))
    return chain


async def refresh_token_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    """The issued token this hash matches, or None for one this platform
    never minted or has already forgotten."""
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def refresh_chain_by_id(session: AsyncSession, chain_id: uuid.UUID) -> RefreshChain | None:
    """The sign-in a refresh token's chain id names, or None if it is gone."""
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
    """End one sign-in: every refresh token issued from this chain stops
    working, whatever token was last handed out."""
    await session.execute(
        update(RefreshChain).where(RefreshChain.id == chain_id).values(revoked_at=at, revoked_reason=reason)
    )


async def revoke_all_chains_for_user(
    session: AsyncSession, *, user_id: uuid.UUID, at: datetime, reason: str
) -> None:
    """End every sign-in this account still has open, such as on logout
    without a specific token, a password change, or a suspicious reset."""
    await session.execute(
        update(RefreshChain)
        .where(RefreshChain.user_id == user_id, RefreshChain.revoked_at.is_(None))
        .values(revoked_at=at, revoked_reason=reason)
    )


# --- password reset --------------------------------------------------------


async def create_reset_token(
    session: AsyncSession, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> PasswordResetToken:
    """Mint a fresh reset link for this account. The caller is responsible
    for spending any earlier unused link first, so only the newest works."""
    token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    return token


async def reset_token_by_hash(session: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    """The reset link this hash matches, or None for one that was never
    issued or that this table has since forgotten."""
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_reset_token_used(session: AsyncSession, *, token_id: uuid.UUID, at: datetime) -> None:
    """Spend this one reset link so it cannot be redeemed a second time."""
    await session.execute(
        update(PasswordResetToken).where(PasswordResetToken.id == token_id).values(used_at=at)
    )


async def mark_unused_reset_tokens_used(session: AsyncSession, *, user_id: uuid.UUID, at: datetime) -> None:
    """Spend every link this account has not used yet.

    Called when a fresh one is minted for the same person, so the last email is
    the only live one. The table does not record which link was an invitation
    and which a reset — they are the same kind of credential — so this spends
    them together, which is the safe direction: it can strand a link nobody has
    clicked, never leave two ways into an account open at once.
    """
    await session.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
        .values(used_at=at)
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


async def update_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str | None,
    exam_date: date | None,
    clear_exam_date: bool,
    exam_code: str | None = None,
    ai_training_consent: bool | None = None,
    colleague_waiting_email: bool | None = None,
    replay_onboarding: bool | None = None,
    exam_time: time | None = None,
    clear_exam_time: bool = False,
    needs_extra_time: bool | None = None,
    custom_reading_seconds: int | None = None,
    clear_custom_reading_seconds: bool = False,
    custom_simulation_seconds: int | None = None,
    clear_custom_simulation_seconds: bool = False,
) -> User | None:
    """Write only what was sent.

    `None` means "leave it" for every field, which is why clearing an exam date, an exam time or
    either custom timer each needs its own flag: a PATCH that cannot distinguish "not mentioned"
    from "set to nothing" makes clearing impossible. Clearing `exam_date` also clears
    `exam_time` (a time with no date names nothing), whether or not the caller asked for that
    explicitly.
    """
    user = await session.get(User, user_id)
    if user is None:
        return None
    if name is not None:
        user.name = name
    if exam_code is not None:
        user.exam_code = exam_code
    if ai_training_consent is not None:
        user.ai_training_consent = ai_training_consent
    if colleague_waiting_email is not None:
        user.colleague_waiting_email = colleague_waiting_email
    if replay_onboarding is not None:
        user.replay_onboarding = replay_onboarding
    if needs_extra_time is not None:
        user.needs_extra_time = needs_extra_time
    if clear_custom_reading_seconds:
        user.custom_reading_seconds = None
    elif custom_reading_seconds is not None:
        user.custom_reading_seconds = custom_reading_seconds
    if clear_custom_simulation_seconds:
        user.custom_simulation_seconds = None
    elif custom_simulation_seconds is not None:
        user.custom_simulation_seconds = custom_simulation_seconds
    if clear_exam_date:
        user.exam_date = None
        user.exam_time = None
    else:
        if exam_date is not None:
            user.exam_date = exam_date
        if clear_exam_time:
            user.exam_time = None
        elif exam_time is not None:
            user.exam_time = exam_time
    await session.flush()
    return user
