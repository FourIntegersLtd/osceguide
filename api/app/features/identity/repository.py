"""Storage for users and their sessions. Mapped classes do not leave this module."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime, time

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity.domain import normalize_email
from app.features.identity.models import (
    PasswordResetToken,
    RefreshChain,
    RefreshToken,
    User,
    UserIdentity,
    UserMfa,
    UserMfaRecoveryCode,
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


async def user_ids_closed_before(session: AsyncSession, *, cutoff: datetime) -> list[uuid.UUID]:
    """Every closed account not yet erased, closed at or before `cutoff`.

    Filters on `erased_at IS NULL` rather than trusting the caller to skip
    ones it already handled — the scheduled erasure job's own idempotency
    check, so a second run the same day finds nothing left to do.
    """
    stmt = select(User.id).where(
        User.status == "deleted",
        User.closed_at.is_not(None),
        User.closed_at <= cutoff,
        User.erased_at.is_(None),
    )
    return list((await session.execute(stmt)).scalars())


async def candidates_for_engagement_email(
    session: AsyncSession, *, window_start: datetime, window_end: datetime
) -> list[User]:
    """Every account signed up inside the lookback window that has not yet
    been sent, or ruled out for, the "come try a station" nudge.

    Only what this slice can answer on its own: the sign-up window and
    `engagement_email_sent_at IS NULL`. `service_engagement.py` still has to
    check each candidate against `attempts` (never completed a station) and
    `roster` (never an institution-provisioned trainee) before sending —
    those tables belong to other slices, so this query cannot see them.
    A closed account (`status == "deleted"`) is excluded here: legacy's own
    `_should_send_engagement_email` refuses a deleted account outright, and
    there is nothing to nudge someone back to if their account is gone.
    """
    stmt = select(User).where(
        User.created_at >= window_start,
        User.created_at <= window_end,
        User.status != "deleted",
        User.engagement_email_sent_at.is_(None),
    )
    return list((await session.execute(stmt)).scalars())


async def claim_engagement_email(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> bool:
    """Atomically mark one account as having been sent the engagement email.

    Returns False, claiming nothing, if it was already sent (by an earlier
    run, or by another worker's identical statement a moment before this
    one) — the same `UPDATE ... WHERE ... IS NULL ... RETURNING` shape as
    `marketplace.repository.claim_due_reminders`, sized to one row at a time
    here because each candidate needs its own cross-slice checks in between
    the select and the claim, unlike a marketplace session's single-table
    check.
    """
    claimed = await session.execute(
        update(User)
        .where(User.id == user_id, User.engagement_email_sent_at.is_(None))
        .values(engagement_email_sent_at=now)
        .returning(User.id)
    )
    return claimed.scalar_one_or_none() is not None


async def scrub_for_erasure(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> bool:
    """Overwrite this account's personal fields and mark it erased.

    Returns False, doing nothing, if the account is gone or already erased —
    the erasure job's per-account idempotency check, alongside
    `user_ids_closed_before`'s own filter, so calling this twice on the same
    account (a retried job run, an overlapping schedule) is always safe.
    """
    user = await session.get(User, user_id)
    if user is None or user.erased_at is not None:
        return False
    user.name = "Deleted user"
    user.email = f"deleted-{user.id}@invalid"
    user.avatar_url = None
    user.erased_at = now
    return True


async def is_erased(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether this account has already been scrubbed by the erasure job.

    The erasure job asks this about the *other* side of a peer-practice
    recording before deleting it on one participant's say-so alone — a
    two-person recording is not erased just because one of them is.
    """
    stmt = select(User.erased_at).where(User.id == user_id)
    erased_at = (await session.execute(stmt)).scalar_one_or_none()
    return erased_at is not None


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


async def set_avatar_url(session: AsyncSession, user_id: uuid.UUID, *, avatar_url: str | None) -> User | None:
    """Write this person's photo URL, or clear it. No `Timestamps.updated_at`
    read follows, so this needs no `session.refresh()`."""
    await session.execute(update(User).where(User.id == user_id).values(avatar_url=avatar_url))
    return await user_by_id(session, user_id)


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


# --- authenticator ---------------------------------------------------------


async def mfa_by_user(session: AsyncSession, user_id: uuid.UUID) -> UserMfa | None:
    """The authenticator row for this account, confirmed or not."""
    return (await session.execute(select(UserMfa).where(UserMfa.user_id == user_id))).scalar_one_or_none()


async def save_pending_mfa_secret(
    session: AsyncSession, user_id: uuid.UUID, *, secret_ciphertext: str, now: datetime
) -> UserMfa:
    """Store a secret that has not been confirmed yet, replacing any previous attempt.

    A confirmed authenticator is never overwritten here. The caller refuses
    that case before asking.
    """
    row = await mfa_by_user(session, user_id)
    if row is None:
        row = UserMfa(user_id=user_id, secret_ciphertext=secret_ciphertext, confirmed_at=None, created_at=now)
        session.add(row)
    else:
        row.secret_ciphertext = secret_ciphertext
        row.confirmed_at = None
        row.last_used_step = None
    await session.flush()
    return row


async def confirm_mfa(session: AsyncSession, user_id: uuid.UUID, *, at: datetime, step: int) -> None:
    """Mark the pending secret as the live authenticator and remember the step just used."""
    await session.execute(
        update(UserMfa).where(UserMfa.user_id == user_id).values(confirmed_at=at, last_used_step=step)
    )


async def set_mfa_last_used_step(session: AsyncSession, user_id: uuid.UUID, step: int) -> None:
    """Remember a TOTP step so the same code cannot be accepted again."""
    await session.execute(update(UserMfa).where(UserMfa.user_id == user_id).values(last_used_step=step))


async def delete_mfa(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Remove the authenticator and every recovery code. The account can enrol again."""
    await session.execute(delete(UserMfaRecoveryCode).where(UserMfaRecoveryCode.user_id == user_id))
    await session.execute(delete(UserMfa).where(UserMfa.user_id == user_id))


async def replace_recovery_codes(session: AsyncSession, user_id: uuid.UUID, code_hashes: list[str]) -> None:
    """Throw away every previous recovery code and store these hashes."""
    await session.execute(delete(UserMfaRecoveryCode).where(UserMfaRecoveryCode.user_id == user_id))
    session.add_all(UserMfaRecoveryCode(user_id=user_id, code_hash=code_hash) for code_hash in code_hashes)
    await session.flush()


async def unused_recovery_codes(session: AsyncSession, user_id: uuid.UUID) -> list[UserMfaRecoveryCode]:
    """Recovery codes that have not been spent."""
    stmt = select(UserMfaRecoveryCode).where(
        UserMfaRecoveryCode.user_id == user_id, UserMfaRecoveryCode.used_at.is_(None)
    )
    return list((await session.execute(stmt)).scalars())


async def count_unused_recovery_codes(session: AsyncSession, user_id: uuid.UUID) -> int:
    """How many recovery codes are left. The codes themselves are not returned."""
    stmt = (
        select(func.count())
        .select_from(UserMfaRecoveryCode)
        .where(UserMfaRecoveryCode.user_id == user_id, UserMfaRecoveryCode.used_at.is_(None))
    )
    return int((await session.execute(stmt)).scalar_one())


async def mark_recovery_code_used(session: AsyncSession, code_id: uuid.UUID, *, at: datetime) -> None:
    """Spend one recovery code. A second presentation finds `used_at` set and is refused."""
    await session.execute(
        update(UserMfaRecoveryCode).where(UserMfaRecoveryCode.id == code_id).values(used_at=at)
    )
