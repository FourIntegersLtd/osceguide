"""Two people claiming one slot at the same moment.

Run on two real connections rather than simulated, because the guarantee being
tested is the database's: without the row lock both transactions read
`available` and both believe they won.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repo
from app.features.identity import repository as identity_repo
from app.features.marketplace import errors, repository, service

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


async def test_only_one_of_two_simultaneous_claims_succeeds(db_session: AsyncSession) -> None:
    """The one test in this project that needs committed data.

    Each claimant runs in its own transaction on its own connection, so the post
    has to be visible to both — which means committing it, outside the
    per-test rollback the other tests rely on.
    """
    from app.core.db import get_session_factory

    factory = get_session_factory()

    # Arrange, committed, on its own connection.
    async with factory() as setup, setup.begin():
        owner = await identity_repo.create_user(
            setup, email=f"o{uuid.uuid4().hex[:8]}@example.com", name="O", password_hash=None
        )
        first = await identity_repo.create_user(
            setup, email=f"a{uuid.uuid4().hex[:8]}@example.com", name="A", password_hash=None
        )
        second = await identity_repo.create_user(
            setup, email=f"b{uuid.uuid4().hex[:8]}@example.com", name="B", password_hash=None
        )
        exam = await catalog_repo.exam_by_code(setup, "sca")
        assert exam is not None
        post = await repository.create_post(
            setup,
            owner_user_id=owner.id,
            exam_id=exam.id,
            starts_at=LATER,
            duration_minutes=30,
            note=None,
        )
        post_id, first_id, second_id = post.id, first.id, second.id

    async def claim(user_id: uuid.UUID) -> str:
        async with factory() as claimant, claimant.begin():
            try:
                await service.claim_slot(claimant, post_id, claimer_user_id=user_id, now=NOW)
            except errors.PostUnavailableError:
                return "refused"
            return "claimed"

    try:
        outcomes = await asyncio.gather(claim(first_id), claim(second_id))
        assert sorted(outcomes) == ["claimed", "refused"], (
            "exactly one claim must win; both winning means the row was never locked"
        )

        async with factory() as check, check.begin():
            row = await repository.post_by_id(check, post_id)
            assert row is not None
            assert row.status == "claimed"
            assert row.claimed_by_user_id in {first_id, second_id}
    finally:
        # Committed data outlives the test transaction, so it is cleaned up here.
        async with factory() as cleanup, cleanup.begin():
            from sqlalchemy import delete

            from app.features.identity.models import User
            from app.features.marketplace.models import AvailabilityPost, PeerSession

            await cleanup.execute(delete(PeerSession).where(PeerSession.post_id == post_id))
            await cleanup.execute(delete(AvailabilityPost).where(AvailabilityPost.id == post_id))
            await cleanup.execute(delete(User).where(User.id.in_([first_id, second_id])))
