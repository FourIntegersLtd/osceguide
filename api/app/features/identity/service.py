"""Identity use cases. Raises AppError subclasses; never commits."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership, Principal
from app.core.memberships import MembershipLookup
from app.core.settings import Settings
from app.features.identity import repository
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

    `created_at` is here because the free-trial rule is decided by how old an
    account is, and `attempts` was reading this slice's table to find out.
    """

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime


# Bound by `main.py` to `roster`, which sits above this slice. An institution
# rosters people by email before they have ever signed in, and `trainees.user_id`
# is how the two halves meet; nothing filled it, so a person invited to a
# sitting and then registering stayed two unconnected records forever.
_on_registered: list[Callable[[AsyncSession, uuid.UUID, str], Awaitable[None]]] = []


def bind_registration_hook(hook: Callable[[AsyncSession, uuid.UUID, str], Awaitable[None]]) -> None:
    _on_registered.clear()
    _on_registered.append(hook)


async def _announce_registration(session: AsyncSession, user_id: uuid.UUID, email: str) -> None:
    if not _on_registered:
        raise RuntimeError(
            "No registration hook bound. app.main.create_app must call bind_registration_hook."
        )
    await _on_registered[0](session, user_id, email)


def user_read(user: User, memberships: list[Membership]) -> UserRead:
    """The profile, with the memberships the caller actually holds.

    `memberships` was hardcoded to `[]` here while the argument was used only
    for the active workspace, so `GET /me` contradicted its own schema, its
    README and the generated client for every user in the product.
    """
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        is_platform_admin=user.is_platform_admin,
        must_change_password=user.must_change_password,
        exam_date=user.exam_date,
        extra_reading_percent=user.extra_reading_percent,
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
    session: AsyncSession, *, email: str, name: str, password: str, settings: Settings, now: datetime
) -> AuthResult:
    try:
        validate_password(password)
    except WeakPassword as exc:
        raise WeakPasswordError(str(exc)) from exc
    if await repository.user_by_email(session, email) is not None:
        raise EmailTaken()
    user = await repository.create_user(
        session, email=email, name=name, password_hash=hash_password(password)
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

    `extra_reading_percent` is an access arrangement and a person sets their
    own, because what it affects is their own practice. It is **not** applied
    to an institution's examination: a circuit's clock is one clock for
    everybody on it, and extending it for one candidate would extend it for
    the rest. Whoever grants an accommodation in an examination hall does it
    to the circuit's timing. See `docs/port-gaps.md`.
    """
    user = await repository.update_profile(
        session,
        principal.user_id,
        name=body.name,
        exam_date=body.exam_date,
        extra_reading_percent=body.extra_reading_percent,
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

    Bound by `main.py` into `core.auth.get_principal`, which is where it is
    enforced: "every route except these" is not a rule fifty routers can be
    trusted to remember. It had no caller at all for the whole build, so a
    provisioned user could roam the entire API.
    """
    return may_call(must_change_password=True, route=route)


async def user_ref_by_email(session: AsyncSession, email: str) -> UserRef | None:
    """The little another slice needs to know about a person.

    `tenancy` adds a membership by email and must not reach into this slice's
    tables to resolve one; this is the service call that answers it.
    """
    user = await repository.user_by_email(session, email)
    return None if user is None else _ref(user)


async def user_ref_by_id(session: AsyncSession, user_id: uuid.UUID) -> UserRef | None:
    """The little another slice needs, by id."""
    user = await repository.user_by_id(session, user_id)
    return None if user is None else _ref(user)


def _ref(user: User) -> UserRef:
    return UserRef(id=user.id, email=user.email, name=user.name, created_at=user.created_at)


async def user_refs_by_ids(session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, UserRef]:
    """The people behind a set of ids, keyed by id.

    For read models that show a name beside a row. They ask once for everybody
    on the screen rather than once per row.
    """
    rows = await repository.users_by_ids(session, list(user_ids))
    return {row.id: _ref(row) for row in rows}


async def search_users(
    session: AsyncSession, *, query: str | None, limit: int, cursor: dict[str, Any] | None
) -> tuple[list[UserRef], str | None]:
    """Find a person by a fragment of their email. Platform support only.

    Exposed for `tenancy`'s console, which sits above this slice. The only
    caller is behind `PlatformAdmin`: this is the one read in the API that
    crosses every tenant at once, and it belongs to the people who answer
    "somebody cannot sign in" rather than to any organisation.
    """
    rows, next_cursor = await repository.search_users(session, query=query, limit=limit, cursor=cursor)
    return [_ref(row) for row in rows], next_cursor


async def count_users(session: AsyncSession) -> int:
    return await repository.count_users(session)


async def set_platform_admin(session: AsyncSession, user_id: uuid.UUID, *, is_admin: bool) -> UserRef:
    """Grant or revoke the console. One function, because they are one decision."""
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise UserNotFound()
    await repository.set_platform_admin(session, user_id, is_admin=is_admin)
    return _ref(user)
