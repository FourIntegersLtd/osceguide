"""The reconciler must notice what is missing, and must not cry wolf about what is not.

A reconciler nobody has seen fail is not one, so each case damages a loaded database or adds
a legacy document that was never loaded, then asserts the exact reason code.
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import TranscriptMessage
from app.migration import loader, reconcile
from app.migration.attempts import attempt_from_transcript
from app.migration.users import merge_users
from tests.migration.test_loader import b2c_transcript, b2c_user
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db


async def _loaded(session: AsyncSession) -> tuple[dict, dict]:
    """One user and one three-turn attempt in the database; returns their legacy documents."""
    await ensure_exam(session, "sca")
    user = b2c_user("alice@example.com", "sca", "fs-1")
    _, ids, _ = await loader.load_users(session, merge_users([user]))
    transcript = b2c_transcript("fs-1", "t-1", turns=3)
    await loader.load_attempts(session, [attempt_from_transcript(transcript, app_type="sca")], user_ids=ids)
    return {**user, "_collection": "users"}, {**transcript, "app_type": "sca", "_collection": "transcripts"}


async def test_a_loaded_user_and_attempt_are_found(db_session: AsyncSession) -> None:
    user, transcript = await _loaded(db_session)

    assert await reconcile.reconcile_users(db_session, [user], set()) == []
    attempt_findings = await reconcile.reconcile_attempts(db_session, [transcript], set())
    reasons = [finding.reason for finding in attempt_findings]
    # The fixture's station was never imported, which is a real finding, and the only one.
    assert reasons == ["station_not_imported"]


async def test_a_user_that_never_arrived_is_missing(db_session: AsyncSession) -> None:
    await _loaded(db_session)
    ghost = {**b2c_user("ghost@example.com", "sca", "fs-404"), "_collection": "users"}

    findings = await reconcile.reconcile_users(db_session, [ghost], set())

    assert [(finding.legacy_id, finding.reason, finding.expected) for finding in findings] == [
        ("fs-404", "missing", False)
    ]


async def test_deleted_and_emailless_users_are_expected_exclusions(db_session: AsyncSession) -> None:
    await _loaded(db_session)
    deleted = {**b2c_user("gone@example.com", "sca", "fs-del"), "_collection": "users"}
    emailless = {**b2c_user("", "sca", "fs-blank"), "_collection": "users"}

    findings = await reconcile.reconcile_users(db_session, [deleted, emailless], {"fs-del"})

    assert {(finding.legacy_id, finding.reason, finding.expected) for finding in findings} == {
        ("fs-del", "deleted", True),
        ("fs-blank", "no_email", True),
    }
    assert reconcile.defects(findings) == []


async def test_a_transcript_that_never_arrived_is_missing(db_session: AsyncSession) -> None:
    await _loaded(db_session)
    ghost = {**b2c_transcript("fs-1", "t-404"), "app_type": "sca", "_collection": "transcripts"}

    findings = await reconcile.reconcile_attempts(db_session, [ghost], set())

    assert [finding.reason for finding in findings] == ["missing"]


async def test_a_lost_turn_shows_up_as_a_count_difference(db_session: AsyncSession) -> None:
    _, transcript = await _loaded(db_session)
    lost_turn = await db_session.scalar(select(TranscriptMessage.id).limit(1))
    await db_session.execute(delete(TranscriptMessage).where(TranscriptMessage.id == lost_turn))

    findings = await reconcile.reconcile_attempts(db_session, [transcript], set())

    assert "count_differs" in {finding.reason for finding in findings}
    detail = next(finding.detail for finding in findings if finding.reason == "count_differs")
    assert detail == "legacy 3, database 2"


async def test_a_transcript_of_a_deleted_account_is_expected(db_session: AsyncSession) -> None:
    ghost = {**b2c_transcript("fs-del", "t-9"), "app_type": "sca", "_collection": "transcripts"}

    findings = await reconcile.reconcile_attempts(db_session, [ghost], {"fs-del"})

    assert [(finding.reason, finding.expected) for finding in findings] == [("deleted", True)]


async def test_a_payment_without_a_plan_or_grant_is_flagged(db_session: AsyncSession) -> None:
    document = {
        "id": "pay-1",
        "payment_intent_id": "pi_missing",
        "_collection": "sca_payments",
    }

    findings = await reconcile.reconcile_payments(db_session, [document])

    assert [finding.reason for finding in findings] == ["missing"]


async def test_an_imported_user_who_deleted_their_account_is_flagged(db_session: AsyncSession) -> None:
    user, _ = await _loaded(db_session)

    findings = await reconcile.reconcile_users(db_session, [user], {"fs-1"})

    assert [(finding.reason, finding.expected) for finding in findings] == [("imported_but_deleted", False)]
