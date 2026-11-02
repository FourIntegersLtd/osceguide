"""A legacy debrief becomes its own debrief attempt, matched to the run it actually discussed."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts.models import Attempt, AttemptLiveCoverage
from app.features.tutor_memory.models import DebriefSummary
from app.migration import b2c_lookups, loader
from app.migration.attempts import attempt_from_transcript
from app.migration.load_b2c_attempt_extras import load_debriefs, load_live_coverage
from app.migration.load_b2c_attempts import migrate_transcripts
from app.migration.users import merge_users
from tests.migration.test_loader import b2c_transcript
from tests.support.catalog import ensure_exam

pytestmark = pytest.mark.db


def _transcript(transcript_id: str, created_at: str) -> dict:
    return {**b2c_transcript("fs-1", transcript_id), "app_type": "sca", "created_at": created_at}


def _debrief(debrief_id: str, created_at: str) -> dict:
    return {
        "debrief_id": debrief_id,
        "app_type": "sca",
        "user_id": "fs-1",
        "mock_id": "m-1",
        "station_id": "s-1",
        "created_at": created_at,
        "key_insights": ["spoke over the patient"],
        "action_plan": [{"text": "slow down", "done": False}],
        "narrative_summary": "Good rapport, rushed the plan.",
    }


async def _ready(session: AsyncSession, *transcripts: dict):  # type: ignore[no-untyped-def]
    """Two retries at the same station, loaded as real attempts; returns (lookups, pairs)."""
    from tests.migration.test_loader import b2c_user

    await ensure_exam(session, "sca")
    report, user_ids, _email_ids = await loader.load_users(
        session, merge_users([b2c_user("alice@example.com", "sca", "fs-1")])
    )
    migrated = [attempt_from_transcript(doc, app_type="sca") for doc in transcripts]
    from app.migration.load_attempts import load_attempts

    await load_attempts(session, migrated, user_ids=user_ids)
    await session.flush()
    pairs = migrate_transcripts(list(transcripts), [], b2c_lookups.StepReport())
    return await b2c_lookups.build(session), pairs


async def test_two_debriefs_on_one_station_each_get_their_own_attempt(db_session: AsyncSession) -> None:
    first = _transcript("t-1", "2026-02-01T10:00:00Z")
    second = _transcript("t-2", "2026-03-01T10:00:00Z")
    lookups, pairs = await _ready(db_session, first, second)

    first_debrief = _debrief("d-1", "2026-02-01T10:30:00Z")
    second_debrief = _debrief("d-2", "2026-03-01T10:30:00Z")
    report = await load_debriefs(db_session, [first_debrief, second_debrief], pairs, lookups)

    assert report.counts["debrief attempts created"] == 2
    assert report.counts["debriefs created"] == 2
    debrief_attempts = (await db_session.scalars(select(Attempt).where(Attempt.kind == "debrief"))).all()
    assert len(debrief_attempts) == 2
    consultations = (await db_session.scalars(select(Attempt).where(Attempt.kind != "debrief"))).all()
    consultation_by_ref = {attempt.legacy_ref: attempt for attempt in consultations}
    early = consultation_by_ref["b2c:transcript_id:t-1"]
    late = consultation_by_ref["b2c:transcript_id:t-2"]
    sources = {debrief.source_attempt_id for debrief in debrief_attempts}
    assert sources == {early.id, late.id}
    summaries = (await db_session.scalars(select(DebriefSummary))).all()
    assert {summary.attempt_id for summary in summaries} == {debrief.id for debrief in debrief_attempts}


async def test_loading_the_same_debrief_twice_adds_nothing(db_session: AsyncSession) -> None:
    transcript = _transcript("t-1", "2026-02-01T10:00:00Z")
    lookups, pairs = await _ready(db_session, transcript)
    debrief = _debrief("d-1", "2026-02-01T10:30:00Z")
    await load_debriefs(db_session, [debrief], pairs, lookups)

    second = await load_debriefs(db_session, [debrief], pairs, lookups)

    assert second.counts["debriefs already there"] == 1
    assert await db_session.scalar(select(func.count()).select_from(DebriefSummary)) == 1
    debrief_count = select(func.count()).select_from(Attempt).where(Attempt.kind == "debrief")
    assert await db_session.scalar(debrief_count) == 1


async def test_a_summary_misplaced_on_the_consultation_is_moved_to_its_debrief_attempt(
    db_session: AsyncSession,
) -> None:
    """A summary written by an earlier, buggy run directly onto the consultation is re-anchored."""
    transcript = _transcript("t-1", "2026-02-01T10:00:00Z")
    lookups, pairs = await _ready(db_session, transcript)
    consultation = await db_session.scalar(select(Attempt).where(Attempt.kind != "debrief"))
    from app.migration.legacy_ids import legacy_row_id

    db_session.add(
        DebriefSummary(
            id=legacy_row_id("sca:debrief:d-1"),
            attempt_id=consultation.id,
            user_id=consultation.user_id,
            exam_id=consultation.exam_id,
            key_insights=[],
            action_plan=[],
            narrative=None,
            model_used="legacy-b2c",
        )
    )
    await db_session.flush()

    report = await load_debriefs(db_session, [_debrief("d-1", "2026-02-01T10:30:00Z")], pairs, lookups)

    assert report.counts["debriefs re-anchored to their own debrief attempt"] == 1
    summary = await db_session.get(DebriefSummary, legacy_row_id("sca:debrief:d-1"))
    assert summary.attempt_id != consultation.id
    debrief_attempt = await db_session.get(Attempt, summary.attempt_id)
    assert debrief_attempt.kind == "debrief"
    assert debrief_attempt.source_attempt_id == consultation.id


async def test_live_coverage_matches_the_run_current_when_it_was_saved(db_session: AsyncSession) -> None:
    first = _transcript("t-1", "2026-02-01T10:00:00Z")
    second = _transcript("t-2", "2026-03-01T10:00:00Z")
    _lookups, pairs = await _ready(db_session, first, second)
    consultations = (await db_session.scalars(select(Attempt))).all()
    early = next(attempt for attempt in consultations if attempt.legacy_ref == "b2c:transcript_id:t-1")

    coverage = {
        "id": "fs-1_m-1_s-1",
        "saved_at": "2026-02-01T10:15:00Z",
        "items": [{"seq": 1, "domain": "history"}],
    }
    report = await load_live_coverage(db_session, [coverage], pairs)

    assert report.counts["coverage created"] == 1
    snapshot = await db_session.scalar(
        select(AttemptLiveCoverage).where(AttemptLiveCoverage.attempt_id == early.id)
    )
    assert snapshot is not None
