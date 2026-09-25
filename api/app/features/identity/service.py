"""Identity use cases. Raises AppError subclasses; never commits."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership, Principal
from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository, repository_platform
from app.features.identity.domain import WeakPassword, may_call, validate_password
from app.features.identity.errors import (
    EmailTaken,
    InvalidCredentials,
    UserNotFound,
    WeakPasswordError,
)
from app.features.identity.models import User
from app.features.identity.schemas import AuthResult, MembershipRead, UpdateMe, UserRead
from app.features.identity.service_sessions import default_workspace_slug, issue
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
        extra_reading_percent=user.extra_reading_percent,
        exam_code=user.exam_code,
        ai_training_consent=user.ai_training_consent,
        colleague_waiting_email=user.colleague_waiting_email,
        replay_onboarding=user.replay_onboarding,
        memberships=[
            MembershipRead(
                org_id=m.org_id,
                org_slug=m.org_slug,
                org_name=m.org_name,
                org_type=m.org_type,
                role=m.role,
                surface=m.surface,
            )
            for m in memberships
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
) -> AuthResult:
    """Open an account, optionally saying which exam it is for.

    The exam code is stored as given, not checked against the catalogue, and grants nothing
    — it only says which exam the screens should open on.
    """
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    if await repository.user_by_email(session, email) is not None:
        raise EmailTaken()
    user = await repository.create_user(
        session, email=email, name=name, password_hash=hash_password(password), exam_code=exam_code
    )
    await _announce_registration(session, user.id, user.email)
    tokens = await issue(session, user, settings=settings, now=now, memberships=[])
    return AuthResult(**tokens.model_dump(), user=user_read(user, []))


async def read_me(
    session: AsyncSession, *, principal: Principal, memberships_for: MembershipLookup
) -> UserRead:
    user = await repository.user_by_id(session, principal.user_id)
    if user is None:
        raise InvalidCredentials()
    memberships = await memberships_for(session, principal.user_id)
    return user_read(user, memberships)


async def update_me(
    session: AsyncSession,
    *,
    principal: Principal,
    body: UpdateMe,
    fields_sent: set[str],
    memberships_for: MembershipLookup,
) -> UserRead:
    """Change what is a person's own to change.

    `extra_reading_percent` is **not** applied to an institution's examination: a circuit's
    clock is one clock for everybody on it. An accommodation there is granted on the
    circuit's timing instead. See `docs/port-gaps.md`.
    """
    user = await repository.update_profile(
        session,
        principal.user_id,
        name=body.name,
        exam_date=body.exam_date,
        extra_reading_percent=body.extra_reading_percent,
        exam_code=body.exam_code,
        ai_training_consent=body.ai_training_consent if "ai_training_consent" in fields_sent else None,
        colleague_waiting_email=(
            body.colleague_waiting_email if "colleague_waiting_email" in fields_sent else None
        ),
        replay_onboarding=body.replay_onboarding if "replay_onboarding" in fields_sent else None,
        # A PATCH that cannot tell "not mentioned" from "set to nothing" makes
        # clearing an exam date impossible.
        clear_exam_date="exam_date" in fields_sent and body.exam_date is None,
    )
    if user is None:
        raise InvalidCredentials()
    memberships = await memberships_for(session, principal.user_id)
    return user_read(user, memberships)


def may_call_with_temporary_password(route: str) -> bool:
    """Whether somebody holding a temporary password may call this operation.

    Bound into `core.auth.get_principal`, which enforces it on every request. It once had no
    caller at all, letting a provisioned user roam the entire API.
    """
    return may_call(must_change_password=True, route=route)


async def user_ref_by_email(session: AsyncSession, email: str) -> UserRef | None:
    """The little another slice needs to know about a person, by email."""
    user = await repository.user_by_email(session, email)
    return None if user is None else _ref(user)


async def user_ref_by_id(session: AsyncSession, user_id: uuid.UUID) -> UserRef | None:
    """The little another slice needs, by id."""
    user = await repository.user_by_id(session, user_id)
    return None if user is None else _ref(user)


def _ref(user: User) -> UserRef:
    return UserRef(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        exam_code=user.exam_code,
    )


async def user_refs_by_ids(session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, UserRef]:
    """The people behind a set of ids, keyed by id. One query for a whole screen rather than
    one per row."""
    rows = await repository.users_by_ids(session, list(user_ids))
    return {row.id: _ref(row) for row in rows}


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
