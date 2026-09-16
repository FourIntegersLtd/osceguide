"""Scoring a delivered transcript, and not scoring it twice."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import EvaluationFailed
from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.jobs import PLATFORM_DEFAULT_POLICY, score_attempt_now
from app.features.catalog import repository as catalog_repo
from app.features.identity import repository as identity_repo
from tests.support.fakes import FakeEvaluator

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def completed_attempt(session: AsyncSession, *, turns: int = 2) -> uuid.UUID:
    user = await identity_repo.create_user(
        session, email=f"s{uuid.uuid4().hex[:8]}@example.com", name="S", password_hash=None
    )
    exam = await catalog_repo.exam_by_code(session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(session, kind="practice", user_id=user.id, exam_id=exam.id)
    for i in range(turns):
        await transcripts.add_chunk(
            session,
            attempt.id,
            message_id=f"m{i}",
            seq=i,
            role="user" if i % 2 == 0 else "assistant",
            message=f"turn {i}",
            spoken_at=NOW,
        )
    await repository.set_status(session, attempt.id, status="running", at=NOW)
    await repository.set_status(session, attempt.id, status="interaction_complete", at=NOW)
    await session.flush()
    return attempt.id


async def score(session: AsyncSession, attempt_id: uuid.UUID, evaluator: FakeEvaluator) -> bool:
    return await score_attempt_now(
        session,
        attempt_id,
        evaluator=evaluator,
        policy_version=PLATFORM_DEFAULT_POLICY,
        framework_id="sca-rcgp-v1",
        now=NOW,
    )


async def test_a_completed_transcript_is_scored_and_stored(db_session: AsyncSession) -> None:
    attempt_id = await completed_attempt(db_session)
    evaluator = FakeEvaluator()
    assert await score(db_session, attempt_id, evaluator)

    results = await transcripts.results_for(db_session, attempt_id)
    assert len(results) == 1
    assert results[0].policy_version == PLATFORM_DEFAULT_POLICY
    assert results[0].payload["overall"] == "G"
    assert evaluator.calls[0]["turns"] == 2


async def test_the_attempt_moves_to_evaluated(db_session: AsyncSession) -> None:
    attempt_id = await completed_attempt(db_session)
    await score(db_session, attempt_id, FakeEvaluator())
    await db_session.flush()
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None and attempt.status == "evaluated"


async def test_running_the_job_twice_scores_once(db_session: AsyncSession) -> None:
    """The queue may deliver a job more than once; a second result for the same
    policy would mean two different verdicts on one performance."""
    attempt_id = await completed_attempt(db_session)
    evaluator = FakeEvaluator()
    assert await score(db_session, attempt_id, evaluator)
    await db_session.flush()
    assert not await score(db_session, attempt_id, evaluator)
    assert len(evaluator.calls) == 1


async def test_a_different_policy_scores_again_beside_the_first(db_session: AsyncSession) -> None:
    attempt_id = await completed_attempt(db_session)
    await score(db_session, attempt_id, FakeEvaluator())
    await db_session.flush()
    await score_attempt_now(
        db_session,
        attempt_id,
        evaluator=FakeEvaluator(payload={"overall": "A"}),
        policy_version="kings-rubric@2",
        framework_id="sca-rcgp-v1",
        now=NOW,
    )
    await db_session.flush()
    results = await transcripts.results_for(db_session, attempt_id)
    assert {r.policy_version for r in results} == {PLATFORM_DEFAULT_POLICY, "kings-rubric@2"}


async def test_an_empty_transcript_fails_the_attempt_rather_than_marking_it(
    db_session: AsyncSession,
) -> None:
    attempt_id = await completed_attempt(db_session, turns=0)
    evaluator = FakeEvaluator()
    assert not await score(db_session, attempt_id, evaluator)
    await db_session.flush()
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None and attempt.status == "failed"
    assert attempt.failed_reason == "empty_transcript"
    assert evaluator.calls == []


async def test_a_failed_evaluation_leaves_the_attempt_markable(db_session: AsyncSession) -> None:
    """The transcript is still held, so a retry can mark it. Failing the attempt
    here would throw away a recording we cannot get back."""
    attempt_id = await completed_attempt(db_session)
    with pytest.raises(EvaluationFailed):
        await score(db_session, attempt_id, FakeEvaluator(fail_times=1))
    await db_session.flush()
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None and attempt.status == "interaction_complete"
    assert await transcripts.results_for(db_session, attempt_id) == []


async def test_an_attempt_that_never_completed_is_not_scored(db_session: AsyncSession) -> None:
    user = await identity_repo.create_user(
        session=db_session, email="ns@example.com", name="N", password_hash=None
    )
    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    await db_session.flush()
    assert not await score(db_session, attempt.id, FakeEvaluator())
