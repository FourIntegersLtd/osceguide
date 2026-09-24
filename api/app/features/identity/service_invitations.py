"""Bringing somebody in before they have chosen a password.

An institution names people by email long before they sign in: a membership
for a tutor, a roster row for a student. Both used to require the person to
have registered first, on their own, unprompted — `tenancy` refused with
`user_not_found` and `roster` left `user_id` empty, so nobody could be put on
a circuit until they happened to sign up.

An invitation creates the account now, with no password, and queues an email
carrying a set-password token. The token is an ordinary reset token, so the
existing `password-reset/confirm` route finishes the job and there is no
second way to set a password. Until then the account cannot sign in at all:
`verify_password` rejects every attempt against an absent hash.
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

    The caller has already established there is no account for this address;
    an existing one is not re-invited, because that would mint a live
    set-password token for somebody who did not ask for one. Sending one to a
    person who was asked and has not answered is `reissue_invitation`.
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

    An institution rosters and invites people by address long before they sign
    in, and the one email can be lost in a spam folder — with no way for an
    administrator to press "send again" a candidate sits unexamined while the
    organisation believes it told them. The link in the first email cannot be
    repeated: only its hash is stored, which is what makes the token worthless
    to whoever intercepts it. So this mints a fresh one through the same path.

    Returns False when there is nothing to re-send: the account has a password,
    so the invitation was taken up and a set-password link is the wrong email
    to be mailing; or the account is gone.

    The link already out there is spent as the new one is minted, so pressing
    "send again" twice does not leave two live ways to set one person's
    password — the same reason `roster` refuses a duplicate address rather than
    inviting it a second time.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None or user.password_hash is not None:
        return False
    await repository.mark_unused_reset_tokens_used(session, user_id=user.id, at=now)
    await _queue_invitation(session, user=user, invited_to=invited_to, now=now)
    return True


async def _queue_invitation(session: AsyncSession, *, user: User, invited_to: str, now: datetime) -> None:
    """The token and the message, which is all an invitation is.

    Shared by both ways of sending one so a re-issued invitation is the same
    email as the first, not a copy that can drift out of step with it.
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
