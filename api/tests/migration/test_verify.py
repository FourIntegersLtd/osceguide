"""Whether verification actually catches a bad load.

A verifier nobody has seen fail is not a verifier, so each check here is run
against a database that has been damaged on purpose.
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import TranscriptMessage
from app.migration import loader, verify
from app.migration.attempts import attempt_from_transcript
from app.migration.users import merge_users
from tests.migration.test_loader import b2c_transcript, b2c_user

pytestmark = pytest.mark.db


async def _loaded(session: AsyncSession, turns: int = 3):  # type: ignore[no-untyped-def]
    _, ids = await loader.load_users(session, merge_users([b2c_user("alice@example.com", "sca", "fs-1")]))
    migrated = [attempt_from_transcript(b2c_transcript("fs-1", "t-1", turns=turns), app_type="sca")]
    await loader.load_attempts(session, migrated, user_ids=ids)
    return migrated


async def test_a_clean_load_verifies(db_session: AsyncSession) -> None:
    migrated = await _loaded(db_session)
    expected = verify.ExpectedCounts(users=1, entitlements=0, attempts=1, messages=3, results=0)

    assert await verify.compare_counts(db_session, expected) == []
    assert await verify.spot_check(db_session, migrated) == []


async def test_a_missing_batch_shows_up_in_the_counts(db_session: AsyncSession) -> None:
    await _loaded(db_session)
    # The export said there were ten attempts and only one arrived.
    expected = verify.ExpectedCounts(users=1, entitlements=0, attempts=10, messages=30, results=0)

    problems = await verify.compare_counts(db_session, expected)

    assert len(problems) == 2
    assert "attempts: export says 10, database has 1" in problems


async def test_a_dropped_turn_is_invisible_to_counts_and_caught_by_the_hash(
    db_session: AsyncSession,
) -> None:
    migrated = await _loaded(db_session)
    victim = await db_session.scalar(select(TranscriptMessage.id).where(TranscriptMessage.seq == 1))
    await db_session.execute(delete(TranscriptMessage).where(TranscriptMessage.id == victim))
    await db_session.flush()

    # Counts agree with a database that has lost a turn, if the export count is
    # wrong in the same way. The hash does not.
    assert await verify.compare_counts(db_session, verify.ExpectedCounts(1, 0, 1, 2, 0)) == []
    problems = await verify.spot_check(db_session, migrated)
    assert len(problems) == 1
    assert "does not match the export" in problems[0]


async def test_reordered_turns_are_caught(db_session: AsyncSession) -> None:
    """The right turns in the wrong order is a different conversation."""
    migrated = await _loaded(db_session)
    await db_session.execute(update(TranscriptMessage).where(TranscriptMessage.seq == 0).values(seq=99))
    await db_session.flush()

    assert await verify.spot_check(db_session, migrated) != []


async def test_truncated_text_is_caught(db_session: AsyncSession) -> None:
    migrated = await _loaded(db_session)
    await db_session.execute(
        update(TranscriptMessage).where(TranscriptMessage.seq == 0).values(message="turn")
    )
    await db_session.flush()

    assert await verify.spot_check(db_session, migrated) != []


async def test_an_attempt_that_never_arrived_is_named(db_session: AsyncSession) -> None:
    _, ids = await loader.load_users(db_session, merge_users([b2c_user("alice@example.com", "sca", "fs-1")]))
    never_loaded = attempt_from_transcript(b2c_transcript("fs-1", "t-missing"), app_type="sca")

    problems = await verify.spot_check(db_session, [never_loaded])

    assert len(problems) == 1
    assert "t-missing" in problems[0]


async def test_rows_made_after_the_cutover_are_not_counted_as_imported(
    db_session: AsyncSession,
) -> None:
    """Verification has to work on a database that is already serving traffic."""
    from app.features.attempts.models import Attempt
    from app.features.catalog.models import Exam
    from app.features.identity.models import User

    await _loaded(db_session)
    user_id = await db_session.scalar(select(User.id))
    exam_id = await db_session.scalar(select(Exam.id).where(Exam.code == "sca"))
    db_session.add(Attempt(kind="practice", user_id=user_id, exam_id=exam_id, status="created"))
    await db_session.flush()

    counts = await verify.imported_counts(db_session)

    assert counts.attempts == 1, "the new attempt has no legacy_ref and is not an import"
