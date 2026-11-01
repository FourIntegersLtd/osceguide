"""The order of a person's grants decides which exam they open on, so it must never be a tie."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from app.features.entitlements import service_access
from app.features.entitlements.models import Entitlement
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
LOW = uuid.UUID("00000000-0000-0000-0000-000000000001")
HIGH = uuid.UUID("ffffffff-ffff-ffff-ffff-fffffffffffe")


async def test_grants_written_together_open_on_the_same_exam_every_time(db_session: AsyncSession) -> None:
    """Two grants of one transaction share `created_at`. The opening exam is the oldest grant, and
    among ties the lower id, so it cannot flip between page loads. The higher id is inserted
    first, so an unordered read (heap order) would answer plab."""
    user = await identity_repo.create_user(
        db_session, email=f"tie-{uuid.uuid4().hex[:8]}@example.com", name="Tie", password_hash=None
    )
    sca = await ensure_exam(db_session, "sca")
    plab = await ensure_exam(db_session, "plab")
    assert sca is not None and plab is not None
    for grant_id, exam in ((HIGH, plab), (LOW, sca)):
        db_session.add(
            Entitlement(
                id=grant_id,
                user_id=user.id,
                exam_id=exam.id,
                source="purchase",
                starts_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    await db_session.flush()

    assert [grant.id for grant in await ent_repo.for_user(db_session, user.id)] == [LOW, HIGH]
    access = await service_access.exam_access_for(db_session, user.id, now=NOW)
    assert access.codes == ("sca", "plab")
    assert access.current == "sca"


async def test_an_older_grant_opens_before_a_newer_one_whatever_the_ids(db_session: AsyncSession) -> None:
    user = await identity_repo.create_user(
        db_session, email=f"age-{uuid.uuid4().hex[:8]}@example.com", name="Age", password_hash=None
    )
    sca = await ensure_exam(db_session, "sca")
    plab = await ensure_exam(db_session, "plab")
    assert sca is not None and plab is not None
    older, newer = datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)
    for grant_id, exam, at in ((LOW, sca, newer), (HIGH, plab, older)):
        db_session.add(
            Entitlement(
                id=grant_id,
                user_id=user.id,
                exam_id=exam.id,
                source="purchase",
                starts_at=at,
                created_at=at,
                updated_at=at,
            )
        )
    await db_session.flush()

    assert [grant.id for grant in await ent_repo.for_user(db_session, user.id)] == [HIGH, LOW]
