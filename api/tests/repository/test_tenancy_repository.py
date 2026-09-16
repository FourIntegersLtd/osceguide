"""Tenancy storage, and the isolation every org-scoped slice must prove."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import decode_cursor
from app.features.identity import repository as identity_repo
from app.features.tenancy import repository

pytestmark = pytest.mark.db


async def make_org(session: AsyncSession, slug: str):  # type: ignore[no-untyped-def]
    org = await repository.create_organization(session, slug=slug, name=slug.title())
    await session.flush()
    return org


async def make_user(session: AsyncSession, email: str):  # type: ignore[no-untyped-def]
    user = await identity_repo.create_user(session, email=email, name=email, password_hash="h")
    await session.flush()
    return user


async def test_org_slug_is_unique_case_insensitively(db_session: AsyncSession) -> None:
    await make_org(db_session, "kings")
    with pytest.raises(IntegrityError):
        await make_org(db_session, "KINGS")


async def test_a_user_may_belong_to_several_organisations(db_session: AsyncSession) -> None:
    """The case b2c could not express at all and b2b carried in an array column."""
    alpha, beta = await make_org(db_session, "alpha"), await make_org(db_session, "beta")
    user = await make_user(db_session, "multi@example.com")
    await repository.add_membership(db_session, org_id=alpha.id, user_id=user.id, role="trainee")
    await repository.add_membership(db_session, org_id=beta.id, user_id=user.id, role="owner")
    await db_session.flush()
    memberships = await repository.memberships_for_user(db_session, user.id)
    assert {m.role for m in memberships} == {"trainee", "owner"}


async def test_the_same_role_cannot_be_granted_twice(db_session: AsyncSession) -> None:
    org = await make_org(db_session, "gamma")
    user = await make_user(db_session, "dupe@example.com")
    await repository.add_membership(db_session, org_id=org.id, user_id=user.id, role="admin")
    await db_session.flush()
    with pytest.raises(IntegrityError):
        await repository.add_membership(db_session, org_id=org.id, user_id=user.id, role="admin")
        await db_session.flush()


async def test_org_b_cannot_read_org_a_memberships(db_session: AsyncSession) -> None:
    """The mandatory isolation test. Every org-scoped repository method takes
    org_id first precisely so this cannot be forgotten."""
    alpha, beta = await make_org(db_session, "alpha2"), await make_org(db_session, "beta2")
    user = await make_user(db_session, "iso@example.com")
    await repository.add_membership(db_session, org_id=alpha.id, user_id=user.id, role="trainee")
    await db_session.flush()

    in_alpha, _ = await repository.list_memberships(db_session, alpha.id, limit=10)
    in_beta, _ = await repository.list_memberships(db_session, beta.id, limit=10)
    assert [m.user_id for m in in_alpha] == [user.id]
    assert in_beta == []


async def test_audit_entries_are_scoped_to_their_organisation(db_session: AsyncSession) -> None:
    alpha, beta = await make_org(db_session, "alpha3"), await make_org(db_session, "beta3")
    actor = await make_user(db_session, "actor@example.com")
    for action in ("first", "second"):
        await repository.write_audit(
            db_session, org_id=alpha.id, actor_user_id=actor.id, actor_email=actor.email, action=action
        )
    await repository.write_audit(
        db_session, org_id=beta.id, actor_user_id=actor.id, actor_email=actor.email, action="elsewhere"
    )
    await db_session.flush()

    entries, _ = await repository.list_audit(db_session, alpha.id, limit=10)
    assert {e.action for e in entries} == {"first", "second"}


async def test_audit_entries_come_back_newest_first(db_session: AsyncSession) -> None:
    """Timestamps are explicit here: entries written in one transaction share a
    `now()`, so real ordering can only be shown across distinct instants."""
    from datetime import UTC, datetime

    org = await make_org(db_session, "ordered")
    actor = await make_user(db_session, "order@example.com")
    for day, action in ((1, "oldest"), (2, "middle"), (3, "newest")):
        await repository.write_audit(
            db_session,
            org_id=org.id,
            actor_user_id=actor.id,
            actor_email=actor.email,
            action=action,
            at=datetime(2026, 9, day, tzinfo=UTC),
        )
    await db_session.flush()

    entries, _ = await repository.list_audit(db_session, org.id, limit=10)
    assert [e.action for e in entries] == ["newest", "middle", "oldest"]


async def test_membership_listing_pages_by_cursor(db_session: AsyncSession) -> None:
    org = await make_org(db_session, "paged")
    for i in range(5):
        user = await make_user(db_session, f"p{i}@example.com")
        await repository.add_membership(db_session, org_id=org.id, user_id=user.id, role="trainee")
    await db_session.flush()

    first, cursor = await repository.list_memberships(db_session, org.id, limit=2)
    assert len(first) == 2 and cursor is not None
    # The repository speaks decoded cursors; `CursorParams` decodes at the HTTP edge
    # so a malformed cursor is a 422 before any query runs.
    second, _ = await repository.list_memberships(db_session, org.id, limit=10, cursor=decode_cursor(cursor))
    assert len(second) == 3
    assert {m.id for m in first}.isdisjoint({m.id for m in second})
