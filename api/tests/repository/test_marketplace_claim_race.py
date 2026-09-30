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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import PUBLIC
from app.features.identity import repository as identity_repo
from app.features.marketplace import errors, repository, service
from app.features.rubrics.models import RubricVersion
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


async def test_only_one_of_two_simultaneous_claims_succeeds(db_session: AsyncSession) -> None:
    """The one test in this project that needs committed data.

    Each claimant runs in its own transaction on its own connection, so the post
    has to be visible to both — which means committing it, outside the
    per-test rollback the other tests rely on.
    """
    from app.core.audience import bind_viewer_audiences
    from app.core.db import get_session_factory
    from app.features.roster.service import audiences_for_viewer

    # This test runs on its own connections rather than through the app, so
    # nothing has wired the seams `create_app` normally wires. Claiming a slot
    # checks the claimant's audiences, which needs this one.
    bind_viewer_audiences(audiences_for_viewer)
    factory = get_session_factory()

    # Arrange, committed, on its own connection.
    async with factory() as setup, setup.begin():
        owner = await identity_repo.create_user(
            setup, email=f"o{uuid.uuid4().hex[:8]}@example.com", name="O", password_hash=None
        )
        owner_id = owner.id
        first = await identity_repo.create_user(
            setup, email=f"a{uuid.uuid4().hex[:8]}@example.com", name="A", password_hash=None
        )
        second = await identity_repo.create_user(
            setup, email=f"b{uuid.uuid4().hex[:8]}@example.com", name="B", password_hash=None
        )
        exam = await ensure_exam(setup, "sca")
        assert exam is not None
        exam_id = exam.id
        rubric_version_id = exam.rubric_version_id
        rubric_id = await setup.scalar(
            select(RubricVersion.rubric_id).where(RubricVersion.id == rubric_version_id)
        )
        post = await repository.create_post(
            setup,
            audience=PUBLIC,
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
            except errors.SlotAlreadyClaimedError:
                # The loser is told somebody else got there first, not that the slot is gone.
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

            from app.features.catalog.models import Exam
            from app.features.identity.models import User
            from app.features.marketplace.models import AvailabilityPost, PeerSession
            from app.features.rubrics.models import Rubric

            await cleanup.execute(delete(PeerSession).where(PeerSession.post_id == post_id))
            await cleanup.execute(delete(AvailabilityPost).where(AvailabilityPost.id == post_id))
            await cleanup.execute(delete(User).where(User.id.in_([first_id, second_id, owner_id])))
            # The exam this test had to write — nothing is seeded — and the
            # rubric behind it. Left behind, they are visible to every other
            # test in the run, including the one that pins the table as empty.
            await cleanup.execute(delete(Exam).where(Exam.id == exam_id))
            await cleanup.execute(delete(RubricVersion).where(RubricVersion.id == rubric_version_id))
            await cleanup.execute(delete(Rubric).where(Rubric.id == rubric_id))
