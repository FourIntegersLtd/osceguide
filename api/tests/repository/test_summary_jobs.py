"""Summarising a conversation, and what happens to the turns afterwards.

The half of this slice with teeth: the session job writes the note and then
deletes the transcript, so the order and the idempotency are the behaviour, not
an implementation detail.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import SummaryFailed
from app.features.assistant import repository as assistant_repo
from app.features.identity import repository as identity_repo
from app.features.tutor_memory import repository, service_summaries
from tests.support.fakes import FakeTranscriptSummariser

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


async def a_session_with_turns(db_session: AsyncSession, email: str) -> tuple[uuid.UUID, uuid.UUID]:
    user = await identity_repo.create_user(
        db_session, email=email, name=email, password_hash=None, is_platform_admin=False
    )
    await db_session.flush()
    row = await assistant_repo.create_session(
        db_session,
        user_id=user.id,
        session_type="dashboard",
        instructions="you are a tutor",
        greeting=None,
        extras={},
        room_name=None,
    )
    for seq, (role, message) in enumerate(
        [("assistant", "How did the hip one go?"), ("user", "I forgot the examination again.")]
    ):
        await assistant_repo.add_message(
            db_session,
            row.id,
            message_id=f"m{seq}",
            seq=seq,
            role=role,
            message=message,
            spoken_at=NOW,
        )
    return row.id, user.id


async def test_the_note_is_written_and_the_turns_are_then_deleted(db_session: AsyncSession) -> None:
    session_id, user_id = await a_session_with_turns(db_session, "sum-happy@example.com")
    summariser = FakeTranscriptSummariser()

    assert await service_summaries.summarise_assistant_session(db_session, session_id, summariser=summariser)

    notes = await repository.notes_of_kind(db_session, user_id, kind="session_summary", limit=5)
    assert [n.body["summary"] for n in notes] == ["We went over the hip consultation."]
    assert notes[0].body["agreed_next_steps"] == [
        {"text": "Offer an examination before the history ends", "done": False}
    ]
    assert await assistant_repo.messages_for(db_session, session_id) == []


async def test_the_summariser_is_given_the_turns_in_order(db_session: AsyncSession) -> None:
    session_id, _ = await a_session_with_turns(db_session, "sum-turns@example.com")
    summariser = FakeTranscriptSummariser()

    await service_summaries.summarise_assistant_session(db_session, session_id, summariser=summariser)

    assert summariser.calls[0]["turns"] == 2
    assert summariser.calls[0]["kind"] == "session_summary"


async def test_a_redelivered_job_writes_nothing_twice(db_session: AsyncSession) -> None:
    """It matters here more than elsewhere: the second half deletes the evidence."""
    session_id, user_id = await a_session_with_turns(db_session, "sum-twice@example.com")

    await service_summaries.summarise_assistant_session(
        db_session, session_id, summariser=FakeTranscriptSummariser()
    )
    assert not await service_summaries.summarise_assistant_session(
        db_session, session_id, summariser=FakeTranscriptSummariser()
    )

    assert len(await repository.notes_of_kind(db_session, user_id, kind="session_summary", limit=5)) == 1


async def test_a_failed_summary_leaves_the_turns_where_they_are(db_session: AsyncSession) -> None:
    """A retry must still have something to summarise."""
    session_id, user_id = await a_session_with_turns(db_session, "sum-fail@example.com")

    with pytest.raises(SummaryFailed):
        await service_summaries.summarise_assistant_session(
            db_session, session_id, summariser=FakeTranscriptSummariser(fail_times=1)
        )

    assert len(await assistant_repo.messages_for(db_session, session_id)) == 2
    assert await repository.notes_of_kind(db_session, user_id, kind="session_summary", limit=5) == []


async def test_a_session_with_no_turns_is_left_alone(db_session: AsyncSession) -> None:
    user = await identity_repo.create_user(
        db_session, email="sum-empty@example.com", name="e", password_hash=None, is_platform_admin=False
    )
    await db_session.flush()
    row = await assistant_repo.create_session(
        db_session,
        user_id=user.id,
        session_type="dashboard",
        instructions="x",
        greeting=None,
        extras={},
        room_name=None,
    )

    assert not await service_summaries.summarise_assistant_session(
        db_session, row.id, summariser=FakeTranscriptSummariser()
    )


async def test_a_session_that_is_gone_is_not_an_error(db_session: AsyncSession) -> None:
    assert not await service_summaries.summarise_assistant_session(
        db_session, uuid.uuid4(), summariser=FakeTranscriptSummariser()
    )


async def test_a_debrief_that_does_not_exist_is_not_an_error(db_session: AsyncSession) -> None:
    assert not await service_summaries.summarise_debrief(
        db_session, uuid.uuid4(), summariser=FakeTranscriptSummariser()
    )


async def a_debrief(db_session: AsyncSession, email: str) -> tuple[uuid.UUID, uuid.UUID]:
    """A finished debrief with turns, built the way the worker leaves one."""
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts import repository_transcript as transcripts
    from tests.support.catalog import ensure_exam

    user = await identity_repo.create_user(
        db_session, email=email, name=email, password_hash=None, is_platform_admin=False
    )
    await db_session.flush()
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    source = await attempts_repo.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    debrief = await attempts_repo.create_attempt(
        db_session,
        kind="debrief",
        user_id=user.id,
        exam_id=exam.id,
        source_attempt_id=source.id,
    )
    for seq, (role, message) in enumerate(
        [("assistant", "What would you change?"), ("user", "Examine before the history ends.")]
    ):
        await transcripts.add_chunk(
            db_session,
            debrief.id,
            message_id=f"d{seq}",
            seq=seq,
            role=role,
            message=message,
            spoken_at=NOW,
        )
    await transcripts.mark_transcript_complete(db_session, debrief.id, runtime_label="test", at=NOW)
    return debrief.id, user.id


DEBRIEF_PAYLOAD = {
    "key_insights": ["We agreed the examination was skipped under time pressure"],
    "action_plan": ['Name the examination out loud: "Before we finish, I would like to examine..."'],
    "narrative_summary": "A thorough history let down by a missing examination.",
    "model_used": "fake-model",
}


async def test_a_debrief_is_summarised_into_insights_and_a_plan(db_session: AsyncSession) -> None:
    attempt_id, user_id = await a_debrief(db_session, "sum-debrief@example.com")

    assert await service_summaries.summarise_debrief(
        db_session, attempt_id, summariser=FakeTranscriptSummariser(payload=DEBRIEF_PAYLOAD)
    )

    row = await repository.debrief_summary_for_attempt(db_session, attempt_id)
    assert row is not None
    assert row.user_id == user_id
    assert row.key_insights == DEBRIEF_PAYLOAD["key_insights"]
    assert row.action_plan == [{"text": DEBRIEF_PAYLOAD["action_plan"][0], "done": False}]
    assert row.narrative == DEBRIEF_PAYLOAD["narrative_summary"]
    assert row.model_used == "fake-model"


async def test_one_debrief_is_summarised_once(db_session: AsyncSession) -> None:
    """Two summaries of one debrief would have the tutor agreeing two plans."""
    attempt_id, _ = await a_debrief(db_session, "sum-debrief-twice@example.com")
    summariser = FakeTranscriptSummariser(payload=DEBRIEF_PAYLOAD)

    assert await service_summaries.summarise_debrief(db_session, attempt_id, summariser=summariser)
    assert not await service_summaries.summarise_debrief(db_session, attempt_id, summariser=summariser)


async def test_a_consultation_is_not_summarised_as_a_debrief(db_session: AsyncSession) -> None:
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts import repository_transcript as transcripts
    from tests.support.catalog import ensure_exam

    user = await identity_repo.create_user(
        db_session,
        email="sum-practice@example.com",
        name="p",
        password_hash=None,
        is_platform_admin=False,
    )
    await db_session.flush()
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=user.id, exam_id=exam.id
    )
    await transcripts.add_chunk(
        db_session, attempt.id, message_id="p0", seq=0, role="user", message="hello", spoken_at=NOW
    )
    await transcripts.mark_transcript_complete(db_session, attempt.id, runtime_label="t", at=NOW)

    assert not await service_summaries.summarise_debrief(
        db_session, attempt.id, summariser=FakeTranscriptSummariser(payload=DEBRIEF_PAYLOAD)
    )
