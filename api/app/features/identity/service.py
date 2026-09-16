"""Identity use cases. Raises AppError subclasses; never commits."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership, Principal
from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository
from app.features.identity.domain import RefreshChain as RefreshChainRules
from app.features.identity.domain import (
    WeakPassword,
    use_refresh_token,
    validate_password,
)
from app.features.identity.errors import (
    AccountSuspended,
    EmailTaken,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidResetToken,
    RefreshTokenReused,
    WeakPasswordError,
)
from app.features.identity.schemas import AuthResult, TokenPair, UserRead
from app.features.identity.tokens import (
    access_token_for,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)


async def _principal_for(session: AsyncSession, user: object, *, memberships: list[Membership]) -> Principal:
    return Principal(
        user_id=user.id,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        memberships=tuple(memberships),
        active_org_slug=memberships[0].org_slug if memberships else None,
        is_platform_admin=user.is_platform_admin,  # type: ignore[attr-defined]
    )


async def _issue(
    session: AsyncSession,
    user: object,
    *,
    settings: Settings,
    now: datetime,
    memberships: list[Membership],
) -> TokenPair:
    principal = await _principal_for(session, user, memberships=memberships)
    raw_refresh, token_hash = new_token()
    await repository.create_refresh_chain(
        session,
        user_id=user.id,  # type: ignore[attr-defined]
        token_hash=token_hash,
        expires_at=now + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
    )
    return TokenPair(
        access_token=access_token_for(principal, settings=settings, now=now),
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_ttl_seconds,
    )


def _user_read(user: object, memberships: list[Membership]) -> UserRead:
    return UserRead(
        id=user.id,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        name=user.name,  # type: ignore[attr-defined]
        is_platform_admin=user.is_platform_admin,  # type: ignore[attr-defined]
        must_change_password=user.must_change_password,  # type: ignore[attr-defined]
        memberships=[],
        active_org_slug=memberships[0].org_slug if memberships else None,
        last_login_at=user.last_login_at,  # type: ignore[attr-defined]
    )


async def register(
    session: AsyncSession, *, email: str, name: str, password: str, settings: Settings, now: datetime
) -> AuthResult:
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    if await repository.user_by_email(session, email) is not None:
        raise EmailTaken()
    user = await repository.create_user(
        session, email=email, name=name, password_hash=hash_password(password)
    )
    tokens = await _issue(session, user, settings=settings, now=now, memberships=[])
    return AuthResult(**tokens.model_dump(), user=_user_read(user, []))


async def login_with_memberships(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    memberships_for: MembershipLookup,
    settings: Settings,
    now: datetime,
) -> AuthResult:
    user = await repository.user_by_email(session, email)
    if user is None or not verify_password(user.password_hash, password):
        raise InvalidCredentials()
    if user.status != "active":
        raise AccountSuspended()
    await repository.record_login(session, user.id, now)
    memberships = await memberships_for(session, user.id)
    tokens = await _issue(session, user, settings=settings, now=now, memberships=memberships)
    return AuthResult(**tokens.model_dump(), user=_user_read(user, memberships))


async def refresh(
    session: AsyncSession,
    *,
    refresh_token: str,
    memberships_for: MembershipLookup,
    settings: Settings,
    now: datetime,
) -> TokenPair:
    presented = hash_token(refresh_token)
    token = await repository.refresh_token_by_hash(session, presented)
    if token is None:
        raise InvalidRefreshToken()
    chain = await repository.refresh_chain_by_id(session, token.chain_id)
    if chain is None:
        raise InvalidRefreshToken()

    decision = use_refresh_token(
        RefreshChainRules(
            chain_id=str(chain.id),
            # A spent token is not the live one. Keeping every issued token is
            # what lets that be seen at all.
            current_token_id="spent" if token.used_at else presented,
            expires_at=chain.expires_at,
            revoked_at=chain.revoked_at,
        ),
        presented_token_id=presented,
        now=now,
    )
    if not decision.accepted:
        if decision.revoke_chain:
            await repository.revoke_refresh_chain(
                session, chain_id=chain.id, at=now, reason=decision.reason or "reuse"
            )
            raise RefreshTokenReused()
        raise InvalidRefreshToken()

    user = await repository.user_by_id(session, chain.user_id)
    if user is None:
        raise InvalidRefreshToken()

    raw_refresh, token_hash = new_token()
    await repository.spend_and_issue(
        session, token_id=token.id, chain_id=chain.id, token_hash=token_hash, at=now
    )
    memberships = await memberships_for(session, user.id)
    principal = await _principal_for(session, user, memberships=memberships)
    return TokenPair(
        access_token=access_token_for(principal, settings=settings, now=now),
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_ttl_seconds,
    )


async def logout(session: AsyncSession, *, user_id: uuid.UUID, now: datetime) -> None:
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="logout")


async def begin_password_reset(
    session: AsyncSession, *, email: str, now: datetime, ttl_minutes: int = 60
) -> str | None:
    """Returns the raw token when the address exists, else None.

    The route answers 202 either way: telling a caller whether an address is
    registered is the whole of an account-enumeration attack.
    """
    user = await repository.user_by_email(session, email)
    if user is None:
        return None
    raw, token_hash = new_token()
    await repository.create_reset_token(
        session, user_id=user.id, token_hash=token_hash, expires_at=now + timedelta(minutes=ttl_minutes)
    )
    return raw


async def confirm_password_reset(session: AsyncSession, *, token: str, password: str, now: datetime) -> None:
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    record = await repository.reset_token_by_hash(session, hash_token(token))
    if record is None or record.used_at is not None or now >= record.expires_at:
        raise InvalidResetToken()
    await repository.mark_reset_token_used(session, token_id=record.id, at=now)
    await repository.set_password_hash(session, record.user_id, hash_password(password))
    # A password change ends every existing session: whoever prompted the reset
    # may be holding one.
    await repository.revoke_all_chains_for_user(
        session, user_id=record.user_id, at=now, reason="password_reset"
    )


async def change_password(
    session: AsyncSession, *, user_id: uuid.UUID, current: str, new: str, now: datetime
) -> None:
    try:
        validate_password(new)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    user = await repository.user_by_id(session, user_id)
    if user is None or not verify_password(user.password_hash, current):
        raise InvalidCredentials()
    await repository.set_password_hash(session, user_id, hash_password(new))
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="password_change")


async def read_me(
    session: AsyncSession, *, principal: Principal, memberships_for: MembershipLookup
) -> UserRead:
    user = await repository.user_by_id(session, principal.user_id)
    if user is None:
        raise InvalidCredentials()
    memberships = await memberships_for(session, principal.user_id)
    return _user_read(user, memberships)
