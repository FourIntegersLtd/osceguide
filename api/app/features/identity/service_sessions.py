"""Signing in, staying signed in, and signing out.

Split from `service.py` along the story: that module is about the account,
this one about the session proving you hold it. Every rule that makes a
session safe — reuse detection, rotation, the suspended account, which
workspace a token lands in — lives here.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership, Principal
from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.core.streams import issue_stream_ticket
from app.features.identity import repository
from app.features.identity.domain import RefreshChain as RefreshChainRules
from app.features.identity.domain import use_refresh_token
from app.features.identity.errors import (
    AccountSuspended,
    InvalidCredentials,
    InvalidRefreshToken,
    PasswordLoginDisabled,
    RefreshTokenReused,
)
from app.features.identity.models import User
from app.features.identity.schemas import AuthResult, StreamTicket, TokenPair
from app.features.identity.tokens import (
    access_token_for,
    hash_token,
    new_token,
    verify_absent_password,
    verify_password,
)


def _principal_for(user: User, *, memberships: list[Membership]) -> Principal:
    """The token's view of a person.

    The landing workspace comes from `tenancy.domain.pick_default_workspace`,
    the rule written for it — three copies of `memberships[0]` used to decide
    this, and the rule itself had no caller.
    """
    return Principal(
        user_id=user.id,
        email=user.email,
        memberships=tuple(memberships),
        active_org_slug=default_workspace_slug(memberships),
        is_platform_admin=user.is_platform_admin,
        must_change_password=user.must_change_password,
    )


# Bound by `main.py` to `tenancy.domain`, which owns the rule. `identity` sits
# below `tenancy`, so the two meet at a seam rather than through an import.
_default_workspace: list[Callable[[list[Membership]], str | None]] = []


def bind_default_workspace(pick: Callable[[list[Membership]], str | None]) -> None:
    _default_workspace.clear()
    _default_workspace.append(pick)


def default_workspace_slug(memberships: list[Membership]) -> str | None:
    if not _default_workspace:
        raise RuntimeError(
            "No default-workspace rule bound. app.main.create_app must call bind_default_workspace."
        )
    return _default_workspace[0](memberships)


async def issue(
    session: AsyncSession,
    user: User,
    *,
    settings: Settings,
    now: datetime,
    memberships: list[Membership],
) -> TokenPair:
    principal = _principal_for(user, memberships=memberships)
    raw_refresh, token_hash = new_token()
    await repository.create_refresh_chain(
        session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(seconds=settings.jwt_refresh_ttl_seconds),
    )
    return TokenPair(
        access_token=access_token_for(principal, settings=settings, now=now),
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_ttl_seconds,
    )


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
    if user is None:
        # Verified against a dummy hash so an unknown address costs the same
        # argon2 work as a known one. The messages already match; without this
        # the response *time* still says whether the account exists.
        verify_absent_password(password)
        raise InvalidCredentials()
    if user.password_login_disabled:
        # Checked before the hash: a hash-less SSO account would fail
        # `verify_password` anyway, but that is an accident of storage, not
        # a stated refusal, and it would not catch an account that somehow
        # does carry a hash (an old row from before SSO was configured).
        raise PasswordLoginDisabled()
    if not verify_password(user.password_hash, password):
        raise InvalidCredentials()
    if user.status != "active":
        raise AccountSuspended()
    await repository.record_login(session, user.id, now)
    memberships = await memberships_for(session, user.id)
    tokens = await issue(session, user, settings=settings, now=now, memberships=memberships)
    from app.features.identity.service import user_read  # noqa: PLC0415 - one direction at import

    return AuthResult(**tokens.model_dump(), user=user_read(user, memberships))


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
    if user.status != "active":
        # Suspending an account has to end its sessions, not wait up to thirty
        # days for the refresh chain to expire on its own.
        await repository.revoke_all_chains_for_user(
            session, user_id=user.id, at=now, reason="account_suspended"
        )
        raise AccountSuspended()

    raw_refresh, token_hash = new_token()
    await repository.spend_and_issue(
        session, token_id=token.id, chain_id=chain.id, token_hash=token_hash, at=now
    )
    memberships = await memberships_for(session, user.id)
    principal = _principal_for(user, memberships=memberships)
    return TokenPair(
        access_token=access_token_for(principal, settings=settings, now=now),
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_ttl_seconds,
    )


async def logout(
    session: AsyncSession, *, user_id: uuid.UUID, refresh_token: str | None, now: datetime
) -> None:
    """End the presented session, or every session when none is named.

    This revoked every chain unconditionally, so signing out on a phone signed
    you out of your laptop — and the README said it revoked the presented one.
    """
    if refresh_token:
        token = await repository.refresh_token_by_hash(session, hash_token(refresh_token))
        if token is not None:
            chain = await repository.refresh_chain_by_id(session, token.chain_id)
            # Somebody else's token ends nothing: it names a chain, and a chain
            # belongs to one person.
            if chain is not None and chain.user_id == user_id:
                await repository.revoke_refresh_chain(session, chain_id=chain.id, at=now, reason="logout")
                return
    await repository.revoke_all_chains_for_user(session, user_id=user_id, at=now, reason="logout")


async def mint_stream_ticket(principal: Principal, *, settings: Settings, now: datetime) -> StreamTicket:
    """One `EventSource` connection's worth of credential.

    Issued here because this module already owns what a token says about a
    person; `core.streams` owns the shape, and the two meet at the same seam
    every other token does.
    """
    return StreamTicket(
        ticket=issue_stream_ticket(principal, settings=settings, now=now),
        expires_in=settings.stream_ticket_ttl_seconds,
    )
