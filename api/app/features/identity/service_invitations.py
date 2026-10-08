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
from app.features.identity.domain import WeakPassword, validate_password
from app.features.identity.errors import WeakPasswordError
from app.features.identity.models import User
from app.features.identity.service import UserRef, _announce_registration, _ref
from app.features.identity.tokens import hash_password, new_token
from app.features.notifications import service as notifications

INVITATION_TTL_DAYS = 7


async def invite_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    invited_to: str,
    now: datetime,
    practice_exam_title: str | None = None,
) -> UserRef:
    """Create an account for `email` and queue the invitation, in one transaction.

    The caller has already established there is no account for this address. Sending a
    fresh link to a person who was asked and has not answered is `reissue_invitation`.
    `practice_exam_title` names the exam an organisation is giving them practice access to,
    which switches the email to the wording that says so; the link and token are the same.
    """
    user = await repository.create_user(
        session, email=email, name=name, password_hash=None, must_change_password=True
    )
    await _queue_invitation(
        session, user=user, invited_to=invited_to, now=now, practice_exam_title=practice_exam_title
    )
    # The same hook registering runs: an invited person may already be on a
    # roster somewhere else, and those rows are waiting for this account.
    await _announce_registration(session, user.id, user.email)
    return _ref(user)


async def seat_user_with_temporary_password(
    session: AsyncSession, *, email: str, password: str, name: str = ""
) -> UserRef:
    """Create an account that can sign in now, with a password the console relays by hand.

    The platform console's fallback for when the invitation email cannot reach anyone
    (an unverified sender domain, a mailbox that is not watched). No email is queued: the
    password is told to the person out of band. `must_change_password` is set, so the
    first sign-in may only change it, and the relayed password stops working from then.
    Raises `WeakPasswordError` for a password `validate_password` rejects, as registering does.
    """
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    user = await repository.create_user(
        session, email=email, name=name, password_hash=hash_password(password), must_change_password=True
    )
    await _announce_registration(session, user.id, user.email)
    return _ref(user)


async def seat_or_invite(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    invited_to: str,
    temporary_password: str | None,
    now: datetime,
) -> UserRef:
    """Create the account for an address that has none: seated with the temporary password
    when one is given (no email), otherwise invited by email. The caller has already found
    that no account exists, and never calls this for one that does."""
    if temporary_password is not None:
        return await seat_user_with_temporary_password(
            session, email=email, password=temporary_password, name=name
        )
    return await invite_user(session, email=email, name=name, invited_to=invited_to, now=now)


async def reissue_temporary_password(
    session: AsyncSession, *, user_id: uuid.UUID, password: str, now: datetime
) -> bool:
    """Replace a relayed password that was lost, for an account that has not yet changed it.

    Only while `must_change_password` is still set: once the person has chosen their own
    password this returns False and touches nothing, so the console never resets a real
    credential. Every session the account holds is ended. Raises `WeakPasswordError` as
    seating does. False also when the account is gone or has no password.
    """
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    user = await repository.user_by_id(session, user_id)
    if user is None or user.password_hash is None or not user.must_change_password:
        return False
    await repository.set_temporary_password_hash(session, user.id, hash_password(password))
    await repository.revoke_all_chains_for_user(
        session, user_id=user.id, at=now, reason="temporary_password_reissued"
    )
    return True


async def reissue_invitation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    invited_to: str,
    now: datetime,
    practice_exam_title: str | None = None,
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
    await _queue_invitation(
        session, user=user, invited_to=invited_to, now=now, practice_exam_title=practice_exam_title
    )
    return True


async def _queue_invitation(
    session: AsyncSession,
    *,
    user: User,
    invited_to: str,
    now: datetime,
    practice_exam_title: str | None = None,
) -> None:
    """The token and the message, which is all an invitation is.

    Shared by both ways of sending one so a re-issued invitation stays the same as the first.
    With `practice_exam_title` it is the practice-access wording (`practice_access_invitation`),
    otherwise the plain one; either way the link finishes through `password-reset/confirm`.
    """
    raw, token_hash = new_token()
    await repository.create_reset_token(
        session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=INVITATION_TTL_DAYS),
    )
    if practice_exam_title is None:
        await notifications.enqueue_email(
            session,
            recipient=user.email,
            subject=f"You have been invited to {invited_to}",
            template_key="invitation",
            payload={"token": raw, "invited_to": invited_to},
            idempotency_key=f"invitation:{token_hash}",
        )
        return
    await notifications.enqueue_email(
        session,
        recipient=user.email,
        subject=f"{invited_to} has given you practice access to {practice_exam_title}",
        template_key="practice_access_invitation",
        payload={"token": raw, "invited_to": invited_to, "exam_title": practice_exam_title},
        idempotency_key=f"invitation:{token_hash}",
    )
