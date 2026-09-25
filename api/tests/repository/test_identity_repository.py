"""What the database itself guarantees about users and sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository
from app.features.identity.models import User

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def test_email_uniqueness_ignores_case(db_session: AsyncSession) -> None:
    """citext, not application discipline. b2c kept one user per product in four
    collections; the merge depends on this holding in the database."""
    await repository.create_user(db_session, email="alice@example.com", name="Alice", password_hash="h")
    await db_session.flush()
    with pytest.raises(IntegrityError):
        await repository.create_user(db_session, email="ALICE@example.com", name="Dup", password_hash="h")
        await db_session.flush()


async def test_a_user_is_found_by_any_casing(db_session: AsyncSession) -> None:
    created = await repository.create_user(db_session, email="bob@example.com", name="Bob", password_hash="h")
    await db_session.flush()
    found = await repository.user_by_email(db_session, "  BOB@Example.com  ")
    assert found is not None and found.id == created.id


async def test_updated_at_is_refreshed_by_the_trigger_not_the_orm(db_session: AsyncSession) -> None:
    """A raw SQL update must still move `updated_at`.

    SQLAlchemy's `onupdate` only fires for ORM flushes, so without the trigger
    any repository that writes with `update()` — which is most of them — would
    silently leave the column stale.

    The stale value has to be planted with the trigger disabled, and the
    assertion made with it back on. Comparing timestamps before and after
    proves nothing instead: Postgres `now()` is transaction time, so two writes
    inside one transaction share a value by design.
    """
    from sqlalchemy import text

    user = await repository.create_user(db_session, email="c@example.com", name="C", password_hash="h")
    await db_session.flush()

    await db_session.execute(text("alter table users disable trigger users_set_updated_at"))
    await db_session.execute(
        text("update users set updated_at = timestamptz '2000-01-01' where id = :i"), {"i": user.id}
    )
    planted = (
        await db_session.execute(text("select updated_at from users where id = :i"), {"i": user.id})
    ).scalar_one()
    assert planted.year == 2000, "the trigger was not actually disabled; the test proves nothing"

    await db_session.execute(text("alter table users enable trigger users_set_updated_at"))
    await db_session.execute(text("update users set name = 'C2' where id = :i"), {"i": user.id})
    after = (
        await db_session.execute(text("select updated_at from users where id = :i"), {"i": user.id})
    ).scalar_one()
    assert after.year > 2000


async def test_a_refresh_chain_rotates_in_place(db_session: AsyncSession) -> None:
    user = await repository.create_user(db_session, email="d@example.com", name="D", password_hash="h")
    await db_session.flush()
    chain = await repository.create_refresh_chain(
        db_session, user_id=user.id, token_hash="hash-1", expires_at=NOW + timedelta(days=30)
    )
    await db_session.flush()
    spent = await repository.refresh_token_by_hash(db_session, "hash-1")
    assert spent is not None
    await repository.spend_and_issue(
        db_session, token_id=spent.id, chain_id=chain.id, token_hash="hash-2", at=NOW
    )
    await db_session.flush()

    # The old token is kept and marked spent, which is what makes replay
    # detectable; a rotation that deleted it would look like a forgery.
    old = await repository.refresh_token_by_hash(db_session, "hash-1")
    assert old is not None and old.used_at is not None
    new = await repository.refresh_token_by_hash(db_session, "hash-2")
    assert new is not None and new.used_at is None


async def test_deleting_a_user_takes_their_sessions(db_session: AsyncSession) -> None:
    user = await repository.create_user(db_session, email="e@example.com", name="E", password_hash="h")
    await db_session.flush()
    await repository.create_refresh_chain(
        db_session, user_id=user.id, token_hash="hash-x", expires_at=NOW + timedelta(days=30)
    )
    await db_session.flush()
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.flush()
    assert await repository.refresh_token_by_hash(db_session, "hash-x") is None
