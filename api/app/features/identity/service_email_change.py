"""A person changing their own sign-in address.

The new address must prove it is theirs: a signed link is mailed to it, and the account moves only
when that link is used. Nothing is stored for the pending change; the link carries it, signed with
the same secret as access tokens and bound to the address the account has now, so using it once
(or after the address has changed some other way) makes every copy worthless.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.features.identity import repository
from app.features.identity.errors import (
    AccountNotFound,
    AccountSuspended,
    InvalidCredentials,
    InvalidEmailChangeToken,
    PasswordLoginDisabled,
    PasswordNotSet,
)
from app.features.identity.tokens import verify_password
from app.features.notifications import service as notifications
from app.features.roster import service as roster

EMAIL_CHANGE_TOKEN_TYPE = "email_change"  # noqa: S105 -- a claim name, not a secret
LINK_LIFETIME = timedelta(hours=1)


def _stamp(password_hash: str | None, email: str) -> str:
    """What the account looked like when the link was sent: a reset or any address change since
    makes it differ, which voids every link still in flight."""
    return hashlib.sha256(f"{password_hash or ''}|{email.lower()}".encode()).hexdigest()[:32]


async def begin_email_change(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    new_email: str,
    current_password: str,
    settings: Settings,
    now: datetime,
) -> None:
    """Mail a confirmation link to the new address once the current password is proved.

    Says nothing about whether the address is already held: the answer is the same either way, so
    the form cannot be used to find out who has an account.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()
    if user.password_login_disabled:
        raise PasswordLoginDisabled()
    if user.password_hash is None:
        raise PasswordNotSet()
    if not verify_password(user.password_hash, current_password):
        raise InvalidCredentials()
    if user.status != "active":
        raise AccountSuspended()
    wanted = new_email.strip().lower()
    if wanted == user.email.lower() or await repository.user_by_email(session, wanted) is not None:
        return
    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "typ": EMAIL_CHANGE_TOKEN_TYPE,
            "sub": str(user.id),
            "old": user.email.lower(),
            "new": wanted,
            "stamp": _stamp(user.password_hash, user.email),
            "iat": int(now.timestamp()),
            "exp": int((now + LINK_LIFETIME).timestamp()),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    await notifications.enqueue_email(
        session,
        recipient=wanted,
        subject="Confirm your new email address",
        template_key="email_change",
        payload={"token": token},
        idempotency_key=f"email_change:{user.id}:{int(now.timestamp())}",
    )
    # The current address hears of the request, so a hijacked session cannot do this quietly.
    await notifications.enqueue_email(
        session,
        recipient=user.email,
        subject="Someone asked to change your OSCE Guide email",
        template_key="email_change_requested",
        payload={"new_email": wanted},
        idempotency_key=f"email_change_requested:{user.id}:{int(now.timestamp())}",
    )


async def confirm_email_change(
    session: AsyncSession, *, token: str, settings: Settings, now: datetime
) -> str:
    """Move the account to the address the link was mailed to, and end every session.

    The roster entries that are this person follow the account, and the old address is told.
    """
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "old", "new"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidEmailChangeToken() from exc
    if claims.get("typ") != EMAIL_CHANGE_TOKEN_TYPE:
        raise InvalidEmailChangeToken()
    user = await repository.user_by_id(session, uuid.UUID(str(claims["sub"])))
    new_email = str(claims["new"])
    if (
        user is None
        or user.email.lower() != claims["old"]
        or claims.get("stamp") != _stamp(user.password_hash, user.email)
        or user.status != "active"
        or await repository.user_by_email(session, new_email) is not None
    ):
        raise InvalidEmailChangeToken()
    old_email = user.email
    try:
        await repository.set_email(session, user.id, new_email)
    except IntegrityError as exc:
        # Another confirmation took the address between the check and the write.
        raise InvalidEmailChangeToken() from exc
    await repository.revoke_all_chains_for_user(session, user_id=user.id, at=now, reason="email_change")
    await roster.follow_account_email(session, user_id=user.id, email=new_email)
    await notifications.enqueue_email(
        session,
        recipient=old_email,
        subject="Your OSCE Guide email address was changed",
        template_key="email_changed_notice",
        payload={"new_email": new_email},
        idempotency_key=f"email_changed_notice:{user.id}:{int(now.timestamp())}",
    )
    return new_email
