"""Deleting a person's station progress touches practice, never an examination."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository, repository_platform
from app.features.sittings.models import Slot
from tests.repository.test_attempts_repository import a_slot, a_user, sca

pytestmark = pytest.mark.db


async def test_delete_progress_keeps_exam_slot_attempts(db_session: AsyncSession) -> None:
    user, exam = await a_user(db_session), await sca(db_session)
    slot = await db_session.get(Slot, await a_slot(db_session))
    assert slot is not None
    version_id, slot_id, user_id = slot.station_version_id, slot.id, user.id
    practice = await repository.create_attempt(
        db_session, kind="practice", user_id=user.id, exam_id=exam.id, station_version_id=version_id
    )
    sat = await repository.create_attempt(
        db_session,
        kind="exam_slot",
        user_id=user.id,
        exam_id=exam.id,
        station_version_id=version_id,
        slot_id=slot_id,
    )

    practice_id, sat_id = practice.id, sat.id
    deleted = await repository_platform.delete_for_user_versions(db_session, user_id, [version_id])
    db_session.expire_all()

    assert deleted == 1
    assert await repository.attempt_by_id(db_session, practice_id) is None
    assert await repository.attempt_by_id(db_session, sat_id) is not None
    progress = await repository_platform.progress_by_version(db_session, user_id)
    assert [(row.station_version_id, row.attempts) for row in progress] == []
