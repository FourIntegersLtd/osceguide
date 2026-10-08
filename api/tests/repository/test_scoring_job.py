"""Scoring a delivered transcript, and not scoring it twice."""

from __future__ import annotations

import uuid
from contextlib import nullcontext
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import EvaluationFailed
from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.domain import NO_MARKING_RUBRIC, SCORING_FAILED
from app.features.attempts.jobs import PLATFORM_DEFAULT_POLICY, score_attempt_job, score_attempt_now
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeEvaluator
from tests.support.rubrics import frozen_definition

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def completed_attempt(session: AsyncSession, *, turns: int = 2) -> uuid.UUID:
    user = await identity_repo.create_user(
        session, email=f"s{uuid.uuid4().hex[:8]}@example.com", name="S", password_hash=None
    )
    exam = await ensure_exam(session, "sca")
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
    # An attempt is marked against the rubric frozen onto it when it was
    # rendered; there is no framework id to look one up by any more, so an
    # attempt with no frozen definition is deliberately unmarkable.
    await repository.freeze_definition(
        session, attempt.id, definition=frozen_definition(str(attempt.id)), at=NOW
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
    # The marks alone: the model is the row's column, not a key the rubric's schema forbids.
    assert results[0].payload == {"overall": "G"}
    assert results[0].model_used == "fake-model"
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
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    await db_session.flush()
    assert not await score(db_session, attempt.id, FakeEvaluator())


async def test_the_last_failed_try_marks_the_attempt_marking_failed_and_says_why(
    db_session: AsyncSession,
) -> None:
    """R-5: after the last try the failure is recorded, not re-raised into a queue nobody reads.
    The attempt keeps its transcript and stays markable, so staff can retry it."""
    attempt_id = await completed_attempt(db_session)
    scored = await score_attempt_job(
        attempt_id,
        build_evaluator=lambda: FakeEvaluator(fail_times=1),
        policy_version=PLATFORM_DEFAULT_POLICY,
        framework_id="sca-rcgp-v1",
        now=NOW,
        last_try=True,
        open_session=lambda: nullcontext(db_session),
    )
    await db_session.flush()
    assert scored is False
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    assert (attempt.status, attempt.failed_reason) == ("interaction_complete", SCORING_FAILED)


async def test_a_mark_after_a_failed_one_clears_the_failure(db_session: AsyncSession) -> None:
    attempt_id = await completed_attempt(db_session)
    await repository.set_scoring_failure(db_session, attempt_id, reason=SCORING_FAILED)
    assert await score(db_session, attempt_id, FakeEvaluator())
    await db_session.flush()
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    await db_session.refresh(attempt)
    assert (attempt.status, attempt.failed_reason) == ("evaluated", None)


async def test_the_scoring_job_runs_four_times_and_only_the_fourth_is_the_last_try() -> None:
    """procrastinate counts `attempts` as failed runs so far: it retries while attempts < 3, so a job
    runs 1 + 3 times, 4 s, 16 s then 64 s apart, and only the run it will not retry is the last."""
    from types import SimpleNamespace

    from app.core.jobs import get_jobs_app
    from app.features.attempts.jobs import SCORING_TASK, is_last_try

    strategy = get_jobs_app().tasks[SCORING_TASK].retry_strategy
    assert strategy is not None
    waits: list[int] = []
    last_tries: list[bool] = []
    attempts = 0
    while True:
        job = SimpleNamespace(attempts=attempts)
        decision = strategy.get_retry_decision(exception=RuntimeError("boom"), job=job)  # type: ignore[arg-type]
        last_tries.append(is_last_try(job))  # type: ignore[arg-type]
        if decision is None:
            break
        assert decision.retry_at is not None
        waits.append(round((decision.retry_at - datetime.now(UTC)).total_seconds()))
        attempts += 1
    assert waits == [4, 16, 64]
    assert last_tries == [False, False, False, True]


async def test_any_error_on_the_last_try_is_recorded_not_just_a_failed_evaluation(
    db_session: AsyncSession,
) -> None:
    class Broken:
        async def evaluate(self, **_: object) -> dict:  # type: ignore[type-arg]
            raise RuntimeError("the evaluator could not be built")

    attempt_id = await completed_attempt(db_session)
    scored = await score_attempt_job(
        attempt_id,
        build_evaluator=Broken,  # type: ignore[arg-type]
        policy_version=PLATFORM_DEFAULT_POLICY,
        framework_id="sca-rcgp-v1",
        now=NOW,
        last_try=True,
        open_session=lambda: nullcontext(db_session),
    )
    await db_session.flush()
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert scored is False and attempt is not None
    assert (attempt.status, attempt.failed_reason) == ("interaction_complete", SCORING_FAILED)


async def test_a_failed_second_policy_does_not_mark_an_evaluated_attempt_failed(
    db_session: AsyncSession,
) -> None:
    attempt_id = await completed_attempt(db_session)
    assert await score(db_session, attempt_id, FakeEvaluator())
    await score_attempt_job(
        attempt_id,
        build_evaluator=lambda: FakeEvaluator(fail_times=1),
        policy_version="other@1",
        framework_id="sca-rcgp-v1",
        now=NOW,
        last_try=True,
        open_session=lambda: nullcontext(db_session),
    )
    await db_session.flush()
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    await db_session.refresh(attempt)
    assert (attempt.status, attempt.failed_reason) == ("evaluated", None)


async def test_a_stale_failure_is_cleared_when_the_policy_is_already_scored(
    db_session: AsyncSession,
) -> None:
    attempt_id = await completed_attempt(db_session)
    assert await score(db_session, attempt_id, FakeEvaluator())
    await repository.set_scoring_failure(db_session, attempt_id, reason=SCORING_FAILED)

    assert await score(db_session, attempt_id, FakeEvaluator()) is False

    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    await db_session.refresh(attempt)
    assert attempt.failed_reason is None


async def test_the_reaper_giving_up_on_a_marking_job_says_so_on_the_attempt(
    db_session: AsyncSession,
) -> None:
    from sqlalchemy import text

    from app.features.attempts.jobs import enqueue_scoring
    from app.features.health.service import reclaim_stalled_jobs

    attempt_id = await completed_attempt(db_session)
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    await enqueue_scoring(db_session, attempt, now=NOW)
    job_id = (
        await db_session.execute(
            text("SELECT id FROM procrastinate_jobs WHERE args->>'attempt_id' = :id"),
            {"id": str(attempt_id)},
        )
    ).scalar_one()

    async def dies_while_running() -> None:
        await db_session.execute(
            text("UPDATE procrastinate_jobs SET status = 'doing', worker_id = NULL WHERE id = :id"),
            {"id": job_id},
        )

    for _ in range(3):
        await dies_while_running()
        assert job_id in (await reclaim_stalled_jobs(db_session))[0]
    await dies_while_running()
    assert job_id in (await reclaim_stalled_jobs(db_session))[1]

    await db_session.refresh(attempt)
    assert (attempt.status, attempt.failed_reason) == ("interaction_complete", SCORING_FAILED)


async def test_a_rescore_of_an_attempt_with_no_rubric_is_refused_and_leaves_it_alone(
    db_session: AsyncSession,
) -> None:
    """A migrated legacy attempt has no frozen rubric: rescoring it must not fail it and free its slot."""
    from app.core.auth import Principal
    from app.features.attempts import errors, service_platform_actions

    user = await identity_repo.create_user(
        session=db_session, email=f"u{uuid.uuid4().hex[:8]}@example.com", name="U", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    await repository.set_status(db_session, attempt.id, status="running", at=NOW)
    await repository.set_status(db_session, attempt.id, status="interaction_complete", at=NOW)
    await db_session.flush()
    staff = Principal(user_id=user.id, email="root@osceguide.com", is_platform_admin=True)

    with pytest.raises(errors.InvalidAttemptState):
        await service_platform_actions.rescore(
            db_session, attempt.id, policy_version=None, actor=staff, now=NOW
        )

    await db_session.refresh(attempt)
    assert (attempt.status, attempt.failed_reason) == ("interaction_complete", None)


async def test_an_attempt_with_no_frozen_rubric_is_failed_when_its_marking_is_queued(
    db_session: AsyncSession,
) -> None:
    """S-2: a transcript for an attempt that cannot be marked says so on the attempt."""
    from app.features.attempts.jobs import enqueue_scoring

    user = await identity_repo.create_user(
        session=db_session, email=f"u{uuid.uuid4().hex[:8]}@example.com", name="U", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    attempt_id = attempt.id
    await repository.set_status(db_session, attempt_id, status="running", at=NOW)
    await repository.set_status(db_session, attempt_id, status="interaction_complete", at=NOW)
    await enqueue_scoring(db_session, attempt, now=NOW)
    await db_session.flush()
    stored = await repository.attempt_by_id(db_session, attempt_id)
    assert stored is not None
    await db_session.refresh(stored)
    assert (stored.status, stored.failed_reason) == ("failed", NO_MARKING_RUBRIC)
