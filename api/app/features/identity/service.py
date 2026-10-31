"""Identity use cases. Raises AppError subclasses; never commits."""

from __future__ import annotations

import io
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership, Principal
from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.catalog import service as catalog
from app.features.identity import repository, repository_platform
from app.features.identity.domain import WeakPassword, may_call, normalize_email, validate_password
from app.features.identity.errors import (
    AccountNotFound,
    EmailTaken,
    ExamAlreadyChosen,
    InvalidAvatarFile,
    UnknownExamError,
    UserNotFound,
    WeakPasswordError,
)
from app.features.identity.models import User
from app.features.identity.schemas import MembershipRead, SignInResult, UpdateMe, UserRead
from app.features.identity.service_sessions import default_workspace_slug
from app.features.identity.tokens import (
    hash_password,
)


@dataclass(frozen=True)
class UserRef:
    """A person, as another slice may see them.

    `created_at` is here because the free-trial rule is decided by how old an account is.
    """

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    # Which exam this account is for. Here rather than looked up per screen:
    # the dashboard turns it into the exam everything opens on, and it is the
    # only answer a trial account — which holds no entitlement — has.
    exam_code: str | None = None
    # True while the account was created by an invitation and nobody has used it yet: no
    # password chosen, never signed in, and not an SSO-only account (which has no password on
    # purpose). A screen listing invited people shows them as "invited" until this clears.
    invitation_pending: bool = False
    must_change_password: bool = False
    # First sign-in; None until then. The free trial counts from here (`trial_started_at`).
    activated_at: datetime | None = None

    @property
    def trial_started_at(self) -> datetime:
        """When the free trial began: the first sign-in, or sign-up for an account not yet used."""
        return self.activated_at or self.created_at


async def _announce_registration(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    """Link a person rostered by email before they had an account."""
    # Imported here: `roster` imports this slice's invitations, which import this module.
    from app.features.roster import service as roster

    await roster.claim_roster_entries(session, user_id, email)


def user_read(user: User, memberships: list[Membership]) -> UserRead:
    """The profile, with the memberships the caller actually holds."""
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        is_platform_admin=user.is_platform_admin,
        must_change_password=user.must_change_password,
        exam_date=user.exam_date,
        exam_time=user.exam_time,
        needs_extra_time=user.needs_extra_time,
        custom_reading_seconds=user.custom_reading_seconds,
        custom_simulation_seconds=user.custom_simulation_seconds,
        exam_code=user.exam_code,
        ai_training_consent=user.ai_training_consent,
        colleague_waiting_email=user.colleague_waiting_email,
        replay_onboarding=user.replay_onboarding,
        avatar_url=user.avatar_url,
        memberships=[
            MembershipRead(
                org_id=membership.org_id,
                org_slug=membership.org_slug,
                org_name=membership.org_name,
                org_type=membership.org_type,
                role=membership.role,
                surface=membership.surface,
            )
            for membership in memberships
        ],
        active_org_slug=default_workspace_slug(memberships),
        last_login_at=user.last_login_at,
    )


async def register(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    password: str,
    settings: Settings,
    now: datetime,
    exam_code: str | None = None,
) -> SignInResult:
    """Open an account, optionally saying which exam it is for.

    The exam code grants nothing — it only says which exam the screens should open on. A code
    naming no published exam is dropped rather than refused: a stale landing-page link should
    not cost somebody their sign-up, and an account without an exam is asked for one the first
    time it opens the app (`update_me`).
    """
    if exam_code is not None and exam_code not in await catalog.exam_codes(session):
        exam_code = None
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    if await repository.user_by_email(session, email) is not None:
        raise EmailTaken()
    user = await repository.create_user(
        session,
        email=email,
        name=name,
        password_hash=hash_password(password),
        exam_code=exam_code,
        # Registering is the first sign-in: the free trial counts from here, not from a later one.
        activated_at=now,
    )
    await _announce_registration(session, user.id, user.email)
    from app.features.identity.service_mfa import finish_password_sign_in

    # Registration is a password sign-in. A new account is not a platform admin
    # and holds no membership, so this mints a session; the gate is the same
    # one login uses, so a later requirement cannot grow a second path.
    return await finish_password_sign_in(
        session, user, settings=settings, now=now, memberships=[], count_as_login=False
    )


async def read_me(
    session: AsyncSession, *, principal: Principal, memberships_for: MembershipLookup
) -> UserRead:
    """The signed-in person, refusing `account_not_found` for a valid token
    naming an account that no longer exists."""
    user = await repository.user_by_id(session, principal.user_id)
    if user is None:
        raise AccountNotFound()
    memberships = await memberships_for(session, principal.user_id)
    return user_read(user, memberships)


AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def upload_avatar(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    content: bytes,
    content_type: str | None,
    settings: Settings,
    memberships_for: MembershipLookup,
) -> UserRead:
    """Replace this person's profile photo. Keyed by a fresh id each time, so
    an old cached copy is never overwritten in place."""
    ext = AVATAR_CONTENT_TYPES.get((content_type or "").lower())
    if ext is None:
        raise InvalidAvatarFile("Upload a JPEG, PNG or WebP image")
    if not content or len(content) > AVATAR_MAX_BYTES:
        raise InvalidAvatarFile("That image is too large (5MB max)")

    from app.features.media_production import service as media_production

    key = f"avatars/{user_id}/{uuid.uuid4()}{ext}"
    url = media_production.upload_image(settings, io.BytesIO(content), key)

    previous = await repository.user_by_id(session, user_id)
    previous_url = previous.avatar_url if previous else None
    user = await repository.set_avatar_url(session, user_id, avatar_url=url)
    if user is None:
        raise AccountNotFound()
    if previous_url:
        media_production.delete_image(settings, previous_url)

    memberships = await memberships_for(session, user_id)
    return user_read(user, memberships)


# What a person can only ever set. Sending nothing for one of these leaves it as it is.
_SET_ONLY_PROFILE_FIELDS = (
    "name",
    "needs_extra_time",
    "ai_training_consent",
    "colleague_waiting_email",
    "replay_onboarding",
)
# What a person can also set back to nothing, by sending it empty.
_CLEARABLE_PROFILE_FIELDS = ("exam_date", "exam_time", "custom_reading_seconds", "custom_simulation_seconds")


def profile_changes(body: UpdateMe, fields_sent: set[str], *, exam_code: str | None) -> dict[str, Any]:
    """The account columns this request changes, and the value each one gets.

    A field the request did not mention is left out, so it is not touched.
    That is the difference between "not mentioned" and "set to nothing":
    without it, an exam date or a custom timer could never be cleared.
    `exam_code` is the exam to set, already decided by `_exam_to_set`.
    """
    changes: dict[str, Any] = {}
    for field_name in _SET_ONLY_PROFILE_FIELDS:
        value = getattr(body, field_name)
        if field_name in fields_sent and value is not None:
            changes[field_name] = value
    for field_name in _CLEARABLE_PROFILE_FIELDS:
        if field_name in fields_sent:
            changes[field_name] = getattr(body, field_name)
    if exam_code is not None:
        changes["exam_code"] = exam_code
    if "exam_date" in changes and changes["exam_date"] is None:
        # A time with no date names nothing, so clearing the date clears the time too.
        changes["exam_time"] = None
    return changes


async def update_me(
    session: AsyncSession,
    *,
    principal: Principal,
    body: UpdateMe,
    fields_sent: set[str],
    memberships_for: MembershipLookup,
) -> UserRead:
    """Change what is a person's own to change.

    The custom reading/simulation timers (`custom_reading_seconds`,
    `custom_simulation_seconds`) are **not** applied to an institution's examination: a
    circuit's clock is one clock for everybody on it. An accommodation there is granted on the
    circuit's timing instead. See `web/docs/BACKLOG.md`, S-2. They only take effect at
    all while `needs_extra_time` is true, matching the retiring client's "Extra reading time"
    checkbox.

    The exam is set here once, by an account that has none, and never changed: see
    `_exam_to_set`.
    """
    changes = profile_changes(
        body, fields_sent, exam_code=await _exam_to_set(session, principal.user_id, body.exam_code)
    )
    user = await repository.update_profile(session, principal.user_id, changes)
    if user is None:
        raise AccountNotFound()
    memberships = await memberships_for(session, principal.user_id)
    return user_read(user, memberships)


async def _exam_to_set(session: AsyncSession, user_id: uuid.UUID, requested: str | None) -> str | None:
    """The exam to write for this request, or `None` to leave it alone.

    An account without an exam may choose one, from the published catalogue. One that has an
    exam may not change it: which exam somebody is on decides what every screen shows them, and
    switching is a support action against what they have bought. Sending the exam they already
    have is not a change, so a form that re-sends the whole profile still saves.
    """
    if requested is None:
        return None
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()
    if user.exam_code == requested:
        return None
    if user.exam_code is not None:
        raise ExamAlreadyChosen()
    if requested not in await catalog.exam_codes(session):
        raise UnknownExamError()
    return requested


def may_call_with_temporary_password(route: str) -> bool:
    """Whether somebody holding a temporary password may call this operation.

    Bound into `core.auth.get_principal`, which enforces it on every request. It once had no
    caller at all, letting a provisioned user roam the entire API.
    """
    return may_call(must_change_password=True, route=route)


def normalized_email(raw: str) -> str:
    """An address as accounts store it, so another slice compares the same value this one does."""
    return normalize_email(raw)


async def user_ref_by_email(session: AsyncSession, email: str) -> UserRef | None:
    """The little another slice needs to know about a person, by email."""
    user = await repository.user_by_email(session, email)
    return None if user is None else _ref(user)


async def user_ref_by_id(session: AsyncSession, user_id: uuid.UUID) -> UserRef | None:
    """The little another slice needs, by id."""
    user = await repository.user_by_id(session, user_id)
    return None if user is None else _ref(user)


def _ref(user: User) -> UserRef:
    """The small, cross-slice shape another feature may hold about a person."""
    return UserRef(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        exam_code=user.exam_code,
        invitation_pending=(
            user.password_hash is None
            and user.legacy_password_hash is None
            and not user.password_login_disabled
            and user.last_login_at is None
        ),
        must_change_password=user.must_change_password,
        activated_at=user.activated_at,
    )


async def user_refs_by_ids(session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, UserRef]:
    """The people behind a set of ids, keyed by id. One query for a whole screen rather than
    one per row."""
    users = await repository.users_by_ids(session, list(user_ids))
    return {user.id: _ref(user) for user in users}


async def emails_with_passwords(session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> list[str]:
    """The addresses, sorted, of those among these people who sign in with a password."""
    return sorted(
        user.email
        for user in await repository.users_by_ids(session, list(user_ids))
        if user.password_hash or user.legacy_password_hash
    )


async def user_ids_matching(session: AsyncSession, term: str) -> list[uuid.UUID]:
    """Ids of every account whose name or email contains `term`. For another
    slice's own search filter, so it never joins `users` itself."""
    return await repository.user_ids_matching(session, term)


async def count_users(session: AsyncSession) -> int:
    return await repository_platform.count_users(session)


async def set_platform_admin(session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool) -> UserRef:
    """Grant or revoke the console. One function, because they are one decision."""
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise UserNotFound()
    await repository_platform.set_platform_admin(session, user_id, is_admin=is_admin)
    refreshed = await repository.user_by_id(session, user_id)
    if refreshed is None:
        raise UserNotFound()
    return _ref(refreshed)


async def account_status(session: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Bound into `core.auth`, which refuses a token for a deactivated account
    on its next request rather than its next refresh."""
    user = await repository.user_by_id(session, user_id)
    return None if user is None else user.status


async def is_platform_admin(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether the stored account is a platform admin now, for what outlives a token (a stream)."""
    user = await repository.user_by_id(session, user_id)
    return user is not None and user.status == "active" and user.is_platform_admin
