"""Signing somebody in through an external identity provider.

The broker verified them; this mints the platform session everybody else uses (ADR 0004).
A partner's SSO user is provisioned on first sign-in and is passwordless, so SSO is the
only way in and `sso_only` advertises a truth rather than a preference. It grants no more
than `login` does: whatever the broker's token claims about roles or access is ignored,
since memberships are read from this database and a claim from the provider cannot widen
anybody's access here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository
from app.features.identity.errors import AccountSuspended
from app.features.identity.models import User
from app.features.identity.schemas import AuthResult
from app.features.identity.service import _announce_registration, user_read
from app.features.identity.service_sessions import issue


async def sign_in_external(
    session: AsyncSession,
    *,
    provider: str,
    subject: str,
    email: str,
    name: str,
    tenant_slug: str | None,
    exam_code: str | None,
    settings: Settings,
    now: datetime,
    memberships_for: MembershipLookup,
    sso_only: bool = False,
) -> AuthResult:
    """Find or provision the user a broker vouched for, and issue a session.

    Deliberately does not call `finish_password_sign_in`. The identity
    provider owns the second factor, so this platform does not ask for
    another one. A password sign-in for the same person still does.

    Resolved by the broker's `(provider, subject)` first, so a person who
    changes their address keeps one account; by email second, so an account
    that already exists is linked rather than duplicated. The link is written
    on the way through either, so the next sign-in resolves by subject.
    """
    link = await repository.identity_by_subject(session, provider, subject)
    user = await repository.user_by_id(session, link.user_id) if link is not None else None
    if user is None:
        user = await repository.user_by_email(session, email)
    if user is None:
        user = await repository.create_user(
            session,
            email=email,
            name=name or email,
            password_hash=None,
            exam_code=exam_code,
            password_login_disabled=sso_only,
        )
        # The same hook registration and invitation run: a partner's trainee may
        # already be on a roster somewhere, and those rows await this account.
        await _announce_registration(session, user.id, user.email)
    elif sso_only and not user.password_login_disabled:
        # An account that existed before this organisation's arrangement was
        # `sso_only` — or was matched by email rather than created here — is
        # brought under the same rule rather than staying password-reachable
        # just because it predates the configuration.
        await repository.disable_password_login(session, user.id)
    if user.status != "active":
        raise AccountSuspended()
    if user.password_hash is not None and (
        user.must_change_password
        or (
            not await repository.has_external_identity(session, user.id)
            and await _began_with_relayed_password(session, user)
        )
    ):
        # Someone else chose this password (an admin's temporary password) and the person never
        # replaced it, or replaced it only after the admin had signed in and changed it
        # themselves (the audit log still says it began relayed): it must not outlive the
        # person first proving the address is theirs through SSO (the first link of any provider;
        # a later provider must not undo a password they chose since). Otherwise an admin who seats an
        # address they do not own keeps a way in after the real owner arrives.
        # Anyone holding that password could also have enrolled an authenticator of their own.
        await repository.clear_password(session, user.id)
        await repository.delete_mfa(session, user.id)
        await repository.revoke_all_chains_for_user(
            session, user_id=user.id, at=now, reason="sso_replaced_temp_password"
        )
        await session.refresh(user)
    if link is None:
        await repository.link_identity(
            session, user_id=user.id, provider=provider, subject=subject, tenant_slug=tenant_slug
        )
    await repository.record_login(session, user.id, now)
    memberships = await memberships_for(session, user.id)
    tokens = await issue(session, user, settings=settings, now=now, memberships=memberships)
    return AuthResult(**tokens.model_dump(), user=user_read(user, memberships))


async def _began_with_relayed_password(session: AsyncSession, user: User) -> bool:
    # Imported here: `tenancy` imports this slice, and the audit log is its table.
    from app.features.tenancy import repository as tenancy_repository

    return await tenancy_repository.temporary_password_was_relayed(session, user_id=user.id, email=user.email)
