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
INVITATION_REMINDER_AFTER_DAYS = 5
_REMINDABLE_TEMPLATES = {"invitation", "practice_access_invitation"}


async def invite_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    invited_to: str,
    now: datetime,
    practice_exam_title: str | None = None,
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
) -> UserRef:
    """Create an account for `email` and queue the invitation, in one transaction.

    The caller has already established there is no account for this address. Sending a
    fresh link to a person who was asked and has not answered is `reissue_invitation`.
    `practice_exam_title` names the exam an organisation is giving them practice access to,
    which switches the email to the wording that says so; the link and token are the same.
    `organization_id` is the organisation sending it, kept on the token for `/auth/invitation/{token}`,
    and `role` the seat it is for (kept there too; None when the link seats nobody).
    """
    user = await repository.create_user(
        session, email=email, name=name, password_hash=None, must_change_password=True
    )
    await _queue_invitation(
        session,
        user=user,
        invited_to=invited_to,
        now=now,
        practice_exam_title=practice_exam_title,
        organization_id=organization_id,
        role=role,
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
        session,
        email=email,
        name=name,
        password_hash=await hash_password(password),
        must_change_password=True,
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
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
) -> UserRef:
    """Create the account for an address that has none: seated with the temporary password
    when one is given (no email), otherwise invited by email. The caller has already found
    that no account exists, and never calls this for one that does."""
    if temporary_password is not None:
        return await seat_user_with_temporary_password(
            session, email=email, password=temporary_password, name=name
        )
    return await invite_user(
        session,
        email=email,
        name=name,
        invited_to=invited_to,
        now=now,
        organization_id=organization_id,
        role=role,
    )


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
    await repository.set_temporary_password_hash(session, user.id, await hash_password(password))
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
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
) -> bool:
    """Send the choose-a-password link again, to an account that never used the first one.

    Only the token's hash is stored, so the first link cannot be repeated; this mints a
    fresh one through the same path and spends the old one from the same organisation, so only
    one ever stays live there; another organisation's invitation to the same person is left alone.

    Returns False when there is nothing to re-send: the account already has a password, or
    the account is gone.
    """
    user = await _user_awaiting_password(session, user_id, organization_id=organization_id, now=now)
    if user is None:
        return False
    await _queue_invitation(
        session,
        user=user,
        invited_to=invited_to,
        now=now,
        practice_exam_title=practice_exam_title,
        organization_id=organization_id,
        role=role,
    )
    return True


async def spend_invitations(
    session: AsyncSession, *, user_id: uuid.UUID, organization_id: uuid.UUID, at: datetime
) -> None:
    """Spend the invitation links this organisation sent this person.

    Called when their last live seat there is revoked, so a link already emailed cannot
    sign them in (`confirm_password_reset`) and `/auth/invitation/{token}` refuses it alike.
    """
    await repository.mark_unused_reset_tokens_used(
        session, user_id=user_id, organization_id=organization_id, at=at
    )


async def _send_reminder(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    invited_to: str,
    now: datetime,
    practice_exam_title: str | None,
    organization_id: uuid.UUID | None,
    role: str | None,
) -> bool:
    """The five-day reminder: a fresh link under the reminder wording. False when nothing is due."""
    user = await _user_awaiting_password(session, user_id, organization_id=organization_id, now=now)
    if user is None:
        return False
    await _queue_token_email(
        session,
        user=user,
        now=now,
        template_key="invitation_reminder",
        subject=f"Your invitation to {invited_to} is still waiting",
        payload={"invited_to": invited_to, "exam_title": practice_exam_title or ""},
        organization_id=organization_id,
        role=role,
    )
    return True


async def _user_awaiting_password(
    session: AsyncSession, user_id: uuid.UUID, *, organization_id: uuid.UUID | None, now: datetime
) -> User | None:
    """The account still waiting to choose a password, with the unused links `organization_id`
    sent it spent (not another organisation's); else None."""
    user = await repository.user_by_id(session, user_id)
    if user is None or user.password_hash is not None or user.legacy_password_hash is not None:
        return None
    # SEC-011: an SSO-only account has no password on purpose, not because it is
    # still waiting to choose one. Re-issuing an invitation to it would mint a
    # set-password token and reopen the password door `password_login_disabled`
    # was set to close. `confirm_password_reset` refuses the same account as a
    # second line; this stops the link ever being sent.
    if user.password_login_disabled:
        return None
    await repository.mark_unused_reset_tokens_used(
        session, user_id=user.id, organization_id=organization_id, at=now
    )
    return user


async def _queue_invitation(
    session: AsyncSession,
    *,
    user: User,
    invited_to: str,
    now: datetime,
    practice_exam_title: str | None = None,
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
) -> None:
    """The token and the message, which is all an invitation is.

    Shared by both ways of sending one so a re-issued invitation stays the same as the first.
    With `practice_exam_title` it is the practice-access wording (`practice_access_invitation`),
    otherwise the plain one; either way the link finishes through `password-reset/confirm`.
    """
    if practice_exam_title is None:
        await _queue_token_email(
            session,
            user=user,
            now=now,
            template_key="invitation",
            subject=f"You have been invited to {invited_to}",
            payload={"invited_to": invited_to},
            organization_id=organization_id,
            role=role,
        )
        return
    await _queue_token_email(
        session,
        user=user,
        now=now,
        template_key="practice_access_invitation",
        subject=f"{invited_to} has given you practice access to {practice_exam_title}",
        payload={"invited_to": invited_to, "exam_title": practice_exam_title},
        organization_id=organization_id,
        role=role,
    )


async def _queue_token_email(
    session: AsyncSession,
    *,
    user: User,
    now: datetime,
    template_key: str,
    subject: str,
    payload: dict[str, str],
    organization_id: uuid.UUID | None = None,
    role: str | None = None,
) -> None:
    """Mint the choose-a-password token and queue the email that carries it."""
    raw, token_hash = new_token()
    await repository.create_reset_token(
        session,
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=INVITATION_TTL_DAYS),
        organization_id=organization_id,
        membership_role=role,
    )
    await notifications.enqueue_email(
        session,
        recipient=user.email,
        subject=subject,
        template_key=template_key,
        payload={"token": raw, **payload},
        idempotency_key=f"invitation:{token_hash}",
    )


async def send_due_invitation_reminders(session: AsyncSession, *, now: datetime) -> int:
    """Remind everyone whose invitation has sat unanswered for five days, once, and say how many.

    The daily job calls this. An invitation is due when its link has under two days left, so
    the window is the last two of the seven. The reminder carries a fresh link and spends the
    old one; its own message is not an invitation, so it is never reminded a second time.
    """
    reminder_window = timedelta(days=INVITATION_TTL_DAYS - INVITATION_REMINDER_AFTER_DAYS)
    waiting = await repository.pending_invitations_expiring_between(
        session, window_start=now, window_end=now + reminder_window
    )
    reminded = 0
    for user, token_hash, organization_id, role in waiting:
        original = await notifications.queued_under(session, f"invitation:{token_hash}")
        if original is None or original[0] not in _REMINDABLE_TEMPLATES:
            continue
        payload = original[1]
        if await _send_reminder(
            session,
            user_id=user.id,
            invited_to=str(payload.get("invited_to", "")),
            now=now,
            practice_exam_title=payload.get("exam_title"),
            organization_id=organization_id,
            role=role,
        ):
            reminded += 1
    return reminded
