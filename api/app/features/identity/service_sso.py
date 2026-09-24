"""Signing somebody in through an external identity provider.

The broker verified them; this mints the platform session everybody else uses
(ADR 0004). Unlike the legacy bridge — which refuses an address it did not
import — a partner's SSO user is provisioned on first sign-in: the institution
vouches for them, so there is no password they could have lost. The account is
passwordless, which is the point — `verify_password` rejects every attempt
against an absent hash, so SSO is the only way in and `sso_only` advertises a
truth rather than a preference.

It grants no more than `login` does. Whatever the broker's token claims about
roles or access is ignored: memberships are read from this database, so a claim
from the provider cannot widen anybody's access here.

Split from `service_sessions.py` for the same reason `service_legacy.py` is —
one file per way in, so retiring a broker is retiring a module.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository
from app.features.identity.errors import AccountSuspended
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
    if link is None:
        await repository.link_identity(
            session, user_id=user.id, provider=provider, subject=subject, tenant_slug=tenant_slug
        )
    await repository.record_login(session, user.id, now)
    memberships = await memberships_for(session, user.id)
    tokens = await issue(session, user, settings=settings, now=now, memberships=memberships)
    return AuthResult(**tokens.model_dump(), user=user_read(user, memberships))
