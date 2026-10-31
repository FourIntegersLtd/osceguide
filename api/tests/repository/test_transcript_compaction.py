"""A transcript read is the same before and after its turns become one document."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.domain import Turn
from app.features.attempts.models import Transcript
from tests.support.transcripts import TURNS_AT, add_turns, an_attempt, row_count

pytestmark = pytest.mark.db

NOW = TURNS_AT


async def test_chunks_for_returns_turns_in_seq_order_from_rows(db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    await transcripts.add_chunk(
        db_session, attempt_id, message_id="b", seq=1, role="doctor", message="second", spoken_at=NOW
    )
    await transcripts.add_chunk(
        db_session, attempt_id, message_id="a", seq=0, role="patient", message="first", spoken_at=NOW
    )

    assert await transcripts.chunks_for(db_session, attempt_id) == [
        Turn("a", 0, "patient", "first", NOW),
        Turn("b", 1, "doctor", "second", NOW),
    ]


async def test_compaction_keeps_every_read_identical(db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    await add_turns(db_session, attempt_id, 5)
    await transcripts.mark_transcript_complete(db_session, attempt_id, runtime_label=None, at=NOW)
    before = await transcripts.chunks_for(db_session, attempt_id)
    ids_before = await transcripts.seen_message_ids(db_session, attempt_id)
    counts_before = await transcripts.chunk_counts_for(db_session, [attempt_id])
    assert not await transcripts.is_compacted(db_session, attempt_id)

    assert await transcripts.compact(db_session, attempt_id) is True
    db_session.expire_all()

    assert len(before) == 5
    assert await transcripts.chunks_for(db_session, attempt_id) == before
    assert (
        await transcripts.seen_message_ids(db_session, attempt_id)
        == ids_before
        == {f"m{i}" for i in range(5)}
    )
    assert await row_count(db_session, attempt_id) == 0
    assert (await transcripts.transcript_for(db_session, attempt_id)).message_count == 5  # type: ignore[union-attr]
    assert await transcripts.chunk_count(db_session, attempt_id) == 5
    assert await transcripts.chunk_counts_for(db_session, [attempt_id]) == counts_before == {attempt_id: 5}
    assert await transcripts.is_compacted(db_session, attempt_id)


async def test_a_second_compaction_changes_nothing(db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    await add_turns(db_session, attempt_id, 3)
    await transcripts.mark_transcript_complete(db_session, attempt_id, runtime_label=None, at=NOW)
    assert await transcripts.compact(db_session, attempt_id) is True
    before = await transcripts.chunks_for(db_session, attempt_id)

    assert await transcripts.compact(db_session, attempt_id) is False
    assert await transcripts.chunks_for(db_session, attempt_id) == before


async def test_an_attempt_with_no_turns_gets_no_empty_document(db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    await transcripts.mark_transcript_complete(db_session, attempt_id, runtime_label=None, at=NOW)

    assert await transcripts.compact(db_session, attempt_id) is False
    db_session.expire_all()

    assert not await transcripts.is_compacted(db_session, attempt_id)
    assert await transcripts.chunks_for(db_session, attempt_id) == []
    assert await transcripts.chunk_count(db_session, attempt_id) == 0
    record = await db_session.scalar(select(Transcript).where(Transcript.attempt_id == attempt_id))
    assert record is not None and record.message_count is None


async def test_compacting_without_a_transcript_record_is_a_no_op(db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    await add_turns(db_session, attempt_id, 2)

    assert await transcripts.compact(db_session, attempt_id) is False
    assert await row_count(db_session, attempt_id) == 2


async def test_lock_transcript_works_before_the_record_exists(db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)

    await transcripts.lock_transcript(db_session, attempt_id)


async def test_only_complete_transcripts_past_the_grace_period_are_ready_newest_first(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    old, older, fresh, incomplete = [await an_attempt(db_session) for _ in range(4)]
    for attempt_id in (old, older, fresh):
        await add_turns(db_session, attempt_id, 1)
    await transcripts.mark_transcript_complete(
        db_session, older, runtime_label=None, at=now - timedelta(days=3)
    )
    await transcripts.mark_transcript_complete(
        db_session, old, runtime_label=None, at=now - timedelta(hours=2)
    )
    await transcripts.mark_transcript_complete(
        db_session, fresh, runtime_label=None, at=now - timedelta(minutes=5)
    )
    db_session.add(Transcript(attempt_id=incomplete, complete=False, delivered_at=now - timedelta(days=9)))
    await db_session.flush()

    ready = await transcripts.attempt_ids_ready_to_compact(db_session, limit=10)

    assert [a for a in ready if a in {old, older, fresh, incomplete}] == [old, older]


async def test_ready_list_excludes_already_compacted_and_respects_limit(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    first, second = await an_attempt(db_session), await an_attempt(db_session)
    for attempt_id in (first, second):
        await add_turns(db_session, attempt_id, 1)
        await transcripts.mark_transcript_complete(
            db_session, attempt_id, runtime_label=None, at=now - timedelta(days=1)
        )
    await transcripts.compact(db_session, first)

    ready = await transcripts.attempt_ids_ready_to_compact(db_session, limit=1)

    assert second in ready and first not in ready
    assert len(ready) == 1


async def test_an_attempt_with_no_rows_is_never_ready(db_session: AsyncSession) -> None:
    empty = await an_attempt(db_session)
    await transcripts.mark_transcript_complete(
        db_session, empty, runtime_label=None, at=datetime.now(UTC) - timedelta(days=1)
    )

    assert empty not in await transcripts.attempt_ids_ready_to_compact(db_session, limit=500)


async def test_the_trial_picker_qualifies_rows_a_document_and_not_neither(db_session: AsyncSession) -> None:
    from_rows, from_document, neither = [await an_attempt(db_session) for _ in range(3)]
    await add_turns(db_session, from_rows, 2)
    await add_turns(db_session, from_document, 2)
    await transcripts.mark_transcript_complete(db_session, from_document, runtime_label=None, at=NOW)
    await transcripts.compact(db_session, from_document)

    items, _ = await repository.trial_candidates(db_session, None, limit=50)

    ids = {attempt.id for attempt in items}
    assert from_rows in ids and from_document in ids and neither not in ids


async def test_a_late_turn_dropped_after_compaction_is_logged_but_a_duplicate_is_not(
    db_session: AsyncSession,
) -> None:
    """A lost turn must not look like a repeat: salvage never had a final delivery to cover it."""
    from structlog.testing import capture_logs

    from app.features.attempts import service_worker
    from app.features.attempts.schemas import TranscriptMessageIn

    attempt_id = await an_attempt(db_session)
    await add_turns(db_session, attempt_id, 2)
    await transcripts.mark_transcript_complete(db_session, attempt_id, runtime_label="salvaged", at=NOW)
    assert await transcripts.compact(db_session, attempt_id) is True

    def post(message_id: str) -> TranscriptMessageIn:
        return TranscriptMessageIn(role="patient", message="x", timestamp=NOW, message_id=message_id, seq=9)

    with capture_logs() as logs:
        await service_worker.accept_chunk(
            db_session, attempt_id, body_attempt_id=str(attempt_id), message=post("m1")
        )
        await service_worker.accept_chunk(
            db_session, attempt_id, body_attempt_id=str(attempt_id), message=post("late")
        )

    dropped = [entry for entry in logs if entry["event"] == "transcript.late_turn_dropped"]
    assert [(e["log_level"], e["attempt_id"], e["message_id"]) for e in dropped] == [
        ("warning", str(attempt_id), "late")
    ]
    assert await row_count(db_session, attempt_id) == 0
