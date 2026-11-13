"""Storage of non-verbal batches and summaries, and what erasure removes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.features.attempts import repository_nonverbal as nonverbal
from app.features.attempts import repository_transcript as transcripts
from tests.support.transcripts import an_attempt

pytestmark = pytest.mark.db

AT = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
SAMPLES = [{"at_ms": 1, "face": True, "away": False, "yaw": 0, "pitch": 0, "smile": 0, "nod": False}]


async def _fill(db_session, attempt_id) -> None:
    """One batch and one summary for this attempt."""
    assert await nonverbal.add_batch(db_session, attempt_id, seq=0, skew_ms=5, samples=SAMPLES, at=AT)
    await nonverbal.save_summary(
        db_session, attempt_id, state="insufficient", facts={}, feedback=None, model_used=None, at=AT
    )


async def test_add_batch_reports_a_duplicate(db_session):
    attempt_id = await an_attempt(db_session)
    assert await nonverbal.add_batch(db_session, attempt_id, seq=0, skew_ms=5, samples=SAMPLES, at=AT) is True
    assert (
        await nonverbal.add_batch(db_session, attempt_id, seq=0, skew_ms=9, samples=SAMPLES, at=AT) is False
    )
    assert [batch.seq for batch in await nonverbal.batches_for(db_session, attempt_id)] == [0]
    assert await nonverbal.has_batches(db_session, attempt_id) is True


async def test_delete_batches_keeps_the_summary(db_session):
    attempt_id = await an_attempt(db_session)
    await _fill(db_session, attempt_id)
    await nonverbal.delete_batches(db_session, [attempt_id])
    assert await nonverbal.has_batches(db_session, attempt_id) is False
    assert (await nonverbal.summary_for(db_session, attempt_id)).state == "insufficient"


@pytest.mark.parametrize(
    "erase", [transcripts.erase_content_for_attempts, transcripts.erase_transcripts_for_attempts]
)
async def test_erasure_removes_the_new_rows(db_session, erase):
    attempt_id = await an_attempt(db_session)
    await _fill(db_session, attempt_id)
    await erase(db_session, [attempt_id])
    assert await nonverbal.has_batches(db_session, attempt_id) is False
    assert await nonverbal.summary_for(db_session, attempt_id) is None
