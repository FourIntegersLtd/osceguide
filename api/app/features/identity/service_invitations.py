"""Bringing somebody in before they have chosen a password.

An invitation creates the account now, with no password, and queues an email carrying a
set-password token. The token is an ordinary reset token, so the existing
`password-reset/confirm` route finishes the job — there is no second way to set a password.
Until then the account cannot sign in: `verify_password` rejects every attempt against an
absent hash.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository
from app.features.identity.models import User
from app.features.identity.service import UserRef, _announce_registration, _ref
from app.features.identity.tokens import new_token
from app.features.notifications import service as notifications

INVITATION_TTL_DAYS = 7


async def invite_user(
    session: AsyncSession, *, email: str, name: str, invited_to: str, now: datetime
) -> UserRef:
    """Create an account for `email` and queue the invitation, in one transaction.

    The caller has already established there is no account for this address. Sending a
    fresh link to a person who was asked and has not answered is `reissue_invitation`.
    """
    user = await repository.create_user(
        session, email=email, name=name, password_hash=None, must_change_password=True
    )
    await _queue_invitation(session, user=user, invited_to=invited_to, now=now)
    # The same hook registering runs: an invited person may already be on a
    # roster somewhere else, and those rows are waiting for this account.
    await _announce_registration(session, user.id, user.email)
    return _ref(user)


async def reissue_invitation(
    session: AsyncSession, *, user_id: uuid.UUID, invited_to: str, now: datetime
) -> bool:
    """Send the choose-a-password link again, to an account that never used the first one.

    Only the token's hash is stored, so the first link cannot be repeated; this mints a
    fresh one through the same path and spends the old one, so only one ever stays live.

    Returns False when there is nothing to re-send: the account already has a password, or
    the account is gone.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None or user.password_hash is not None:
        return False
    # SEC-011: an SSO-only account has no password on purpose, not because it is
    # still waiting to choose one. Re-issuing an invitation to it would mint a
    # set-password token and reopen the password door `password_login_disabled`
    # was set to close. `confirm_password_reset` refuses the same account as a
    # second line; this stops the link ever being sent.
    if user.password_login_disabled:
        return False
    await repository.mark_unused_reset_tokens_used(session, user_id=user.id, at=now)
    await _queue_invitation(session, user=user, invited_to=invited_to, now=now)
    return True


async def _queue_invitation(session: AsyncSession, *, user: User, invited_to: str, now: datetime) -> None:
    """The token and the message, which is all an invitation is.

    Shared by both ways of sending one so a re-issued invitation stays the same as the first.
    """
    raw, token_hash = new_token()
    await repository.create_reset_token(
        session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=INVITATION_TTL_DAYS),
    )
    await notifications.enqueue_email(
        session,
        recipient=user.email,
        subject=f"You have been invited to {invited_to}",
        template_key="invitation",
        payload={"token": raw, "invited_to": invited_to},
        idempotency_key=f"invitation:{token_hash}",
    )
