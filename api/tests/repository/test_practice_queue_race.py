"""Two people tapping "practise" at the same instant.

The service reads the queue and then inserts. Two requests in flight together
both find it empty, both insert, and the partial unique index catches the
loser — which used to surface as a 500 rather than the place they already hold.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audience import PUBLIC
from app.features.identity import repository as identity_repo
from app.features.peer_practice import repository
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db


async def test_a_second_insert_yields_nothing_rather_than_raising(db_session: AsyncSession) -> None:
    user = await identity_repo.create_user(
        session=db_session, email="race-queue@example.com", name="R", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None

    first = await repository.join(db_session, user_id=user.id, exam_id=exam.id, audience=PUBLIC)
    second = await repository.join(db_session, user_id=user.id, exam_id=exam.id, audience=PUBLIC)

    assert first is not None
    assert second is None, "the loser of the race must be told, not raised at"
    held = await repository.live_entry(db_session, user.id, exam.id)
    assert held is not None and held.id == first.id


async def test_leaving_twice_reports_the_second_attempt(db_session: AsyncSession) -> None:
    from datetime import UTC, datetime

    user = await identity_repo.create_user(
        session=db_session, email="race-leave@example.com", name="R", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    entry = await repository.join(db_session, user_id=user.id, exam_id=exam.id, audience=PUBLIC)
    assert entry is not None

    now = datetime.now(UTC)
    assert await repository.leave(db_session, entry.id, at=now) is True
    assert await repository.leave(db_session, entry.id, at=now) is False
