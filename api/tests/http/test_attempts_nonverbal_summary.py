"""Writing the non-verbal section after a consultation: facts, one model call, stored once."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.features.attempts import repository, service_nonverbal, service_privacy
from app.features.attempts import repository_nonverbal as nonverbal
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.jobs import PLATFORM_DEFAULT_POLICY, score_attempt_now
from app.features.attempts.jobs_nonverbal import run
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeEvaluator, FakeTranscriptSummariser
from tests.support.rubrics import frozen_definition
from tests.support.sessions import opener_for
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

T0 = datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)
T0_MS = int(T0.timestamp() * 1000)
TURN_ENDS = [
    (0, "user", 10, "Hello, I am Dr Khan"),
    (1, "assistant", 30, "My chest has been tight"),
    (2, "user", 60, "Tell me more about it"),
]
PAYLOAD = {
    "summary": "You faced the screen most of the time.",
    "strengths": ["You nodded while the patient spoke."],
    "observations": [
        {
            "turn_seq": 1,
            "behaviour": "You looked away for 8 seconds.",
            "suggestion": "Look back sooner.",
            "at_seconds": 999,
            "quote": "invented",
        },
        {"turn_seq": 0, "behaviour": "Not a notable turn.", "suggestion": "Ignored."},
        {"turn_seq": 77, "behaviour": "No such turn.", "suggestion": "Ignored."},
    ],
}


def _samples(count: int, *, away=range(0)) -> list[dict]:
    """One-second samples starting at T0; those in `away` face away from the screen."""
    return [
        {
            "at_ms": T0_MS + i * 1000,
            "face": True,
            "away": i in away,
            "yaw": 0,
            "pitch": 0,
            "smile": 0,
            "nod": False,
        }
        for i in range(count)
    ]


async def _finished(db_session, *, seconds: int, away=range(0), email: str | None = None):
    """An evaluated-ready attempt with turns and `seconds` of stored video samples."""
    user = (await identity_repo.user_by_email(db_session, email)) if email else None
    if user is None:
        user = await identity_repo.create_user(
            db_session, email=f"nv{uuid.uuid4().hex[:8]}@example.com", name="N", password_hash=None
        )
    exam = await ensure_exam(db_session, "sca")
    attempt = await repository.create_attempt(db_session, kind="practice", user_id=user.id, exam_id=exam.id)
    for seq, role, end, message in TURN_ENDS:
        await transcripts.add_chunk(
            db_session,
            attempt.id,
            message_id=f"m{seq}",
            seq=seq,
            role=role,
            message=message,
            spoken_at=T0 + timedelta(seconds=end),
        )
    await repository.freeze_definition(
        db_session, attempt.id, definition=frozen_definition(str(attempt.id)), at=T0
    )
    await repository.set_status(db_session, attempt.id, status="running", at=T0)
    await repository.set_status(db_session, attempt.id, status="interaction_complete", at=T0)
    await nonverbal.upsert_consent(db_session, user.id, version="2026-11", at=T0)
    if seconds:
        await nonverbal.add_batch(
            db_session, attempt.id, seq=0, skew_ms=0, samples=_samples(seconds, away=away), at=T0
        )
    await db_session.flush()
    return user, attempt.id


async def _summarise(db_session, attempt_id, summariser) -> bool:
    return await service_nonverbal.summarise(
        opener_for(db_session), attempt_id, summariser=summariser, now=T0
    )


async def test_a_finished_attempt_ends_ready_with_the_batches_deleted(db_session):
    _, attempt_id = await _finished(db_session, seconds=70, away=range(20, 28))
    summariser = FakeTranscriptSummariser(payload=PAYLOAD)
    assert await _summarise(db_session, attempt_id, summariser) is True
    row = await nonverbal.summary_for(db_session, attempt_id)
    assert (row.state, await nonverbal.has_batches(db_session, attempt_id)) == ("ready", False)
    assert row.feedback["observations"] == [
        {"turn_seq": 1, "behaviour": "You looked away for 8 seconds.", "suggestion": "Look back sooner."}
    ]
    assert len(summariser.calls) == 1
    # The fixture's rubric has no framework, so the exam's own words fall back to the default.
    assert str(summariser.calls[0]["instructions"]).endswith(
        "This exam calls these skills: Non-verbal communication; Non-verbal communication; "
        "Non-verbal communication. Use those names where you name a skill."
    )


async def test_the_read_fills_time_and_quote_from_the_facts_not_the_model(db_session, client, make_actor):
    token = await make_actor("nv-sum@example.com")
    _, attempt_id = await _finished(db_session, seconds=70, away=range(20, 28), email="nv-sum@example.com")
    await _summarise(db_session, attempt_id, FakeTranscriptSummariser(payload=PAYLOAD))
    body = (await client.get(f"/api/v1/attempts/{attempt_id}/nonverbal", headers=bearer(token))).json()
    assert body["state"] == "ready"
    assert body["summary"] == {
        "summary": "You faced the screen most of the time.",
        "strengths": ["You nodded while the patient spoke."],
        "observations": [
            {
                "at_seconds": 20,
                "quote": "My chest has been tight",
                "behaviour": "You looked away for 8 seconds.",
                "suggestion": "Look back sooner.",
            }
        ],
        "facing_percent": 89,
        "nods": 0,
    }


async def test_too_little_video_never_calls_the_summariser(db_session):
    _, attempt_id = await _finished(db_session, seconds=30)
    summariser = FakeTranscriptSummariser()
    assert await _summarise(db_session, attempt_id, summariser) is True
    assert summariser.calls == []
    row = await nonverbal.summary_for(db_session, attempt_id)
    assert (row.state, row.feedback, await nonverbal.has_batches(db_session, attempt_id)) == (
        "insufficient",
        None,
        False,
    )


async def test_nothing_owed_means_nothing_happens(db_session):
    _, no_video = await _finished(db_session, seconds=0)
    _, done = await _finished(db_session, seconds=70)
    summariser = FakeTranscriptSummariser(payload=PAYLOAD)
    assert await _summarise(db_session, no_video, summariser) is False
    assert await _summarise(db_session, done, summariser) is True
    assert await _summarise(db_session, done, summariser) is False
    assert len(summariser.calls) == 1


async def test_a_failing_model_raises_for_a_retry_and_stores_nothing(db_session):
    _, attempt_id = await _finished(db_session, seconds=70)
    with pytest.raises(Exception, match="fake failure"):
        await _summarise(db_session, attempt_id, FakeTranscriptSummariser(fail_times=1))
    assert await nonverbal.summary_for(db_session, attempt_id) is None
    assert await nonverbal.has_batches(db_session, attempt_id) is True


async def test_the_last_failed_try_stores_failed_with_the_facts(db_session):
    _, attempt_id = await _finished(db_session, seconds=70, away=range(20, 28))
    opener = opener_for(db_session)
    kwargs = {"build_summariser": lambda: FakeTranscriptSummariser(fail_times=9), "now": T0}
    with pytest.raises(Exception, match="fake failure"):
        await run(opener, attempt_id, last_try=False, **kwargs)
    assert await nonverbal.summary_for(db_session, attempt_id) is None
    assert await run(opener, attempt_id, last_try=True, **kwargs) is False
    row = await nonverbal.summary_for(db_session, attempt_id)
    assert (row.state, row.feedback, row.facts["facing_percent"]) == ("failed", None, 89)
    assert await nonverbal.has_batches(db_session, attempt_id) is False


async def test_the_mark_is_byte_identical_with_and_without_the_feature(db_session):
    results = []
    for seconds in (0, 70):
        _, attempt_id = await _finished(db_session, seconds=seconds, away=range(20, 28))
        if seconds:
            await _summarise(db_session, attempt_id, FakeTranscriptSummariser(payload=PAYLOAD))
        evaluator = FakeEvaluator()
        await score_attempt_now(
            opener_for(db_session),
            attempt_id,
            evaluator=evaluator,
            policy_version=PLATFORM_DEFAULT_POLICY,
            framework_id="sca-rcgp-v1",
            now=T0,
        )
        await db_session.flush()
        (result,) = await transcripts.results_for(db_session, attempt_id)
        results.append((json.dumps(result.payload, sort_keys=True), evaluator.calls[0]["turns"]))
    assert results[0] == results[1]


async def test_finishing_a_consultation_with_video_queues_one_job_and_without_queues_none(db_session):
    from app.features.attempts import service_worker

    async def queued(attempt_id) -> int:
        return int(
            await db_session.scalar(
                text(
                    "SELECT count(*) FROM procrastinate_jobs WHERE task_name = 'summarise_attempt_nonverbal' "
                    "AND args->>'attempt_id' = :i"
                ),
                {"i": str(attempt_id)},
            )
        )

    _, with_video = await _finished(db_session, seconds=70)
    _, without = await _finished(db_session, seconds=0)
    for attempt_id in (with_video, without):
        attempt = await repository.attempt_by_id(db_session, attempt_id)
        await service_worker.complete_interaction(db_session, attempt, now=T0)
    assert (await queued(with_video), await queued(without)) == (1, 0)


class _WithdrawingSummariser(FakeTranscriptSummariser):
    """Withdraws the person's consent while the model is 'thinking', as a concurrent request would."""

    def __init__(self, db_session, user_id) -> None:
        super().__init__(payload=PAYLOAD)
        self._db, self._user_id = db_session, user_id

    async def summarise(self, **kwargs):
        await service_nonverbal.set_consent(
            self._db, self._user_id, consented=False, version="2026-11", now=T0
        )
        return await super().summarise(**kwargs)


async def test_consent_withdrawn_while_the_model_thinks_stores_no_summary(db_session):
    user, attempt_id = await _finished(db_session, seconds=70)
    summariser = _WithdrawingSummariser(db_session, user.id)
    assert await _summarise(db_session, attempt_id, summariser) is False
    assert await nonverbal.summary_for(db_session, attempt_id) is None
    assert await nonverbal.has_batches(db_session, attempt_id) is False


async def test_the_sweep_clears_old_batches_of_abandoned_attempts_and_late_ones_after_a_summary(db_session):
    old = T0 - timedelta(hours=25)
    _, abandoned = await _finished(db_session, seconds=0)
    await repository.set_status(db_session, abandoned, status="failed", at=T0)
    await nonverbal.add_batch(db_session, abandoned, seq=0, skew_ms=0, samples=_samples(5), at=old)
    _, summarised = await _finished(db_session, seconds=70)
    await _summarise(db_session, summarised, FakeTranscriptSummariser(payload=PAYLOAD))
    await nonverbal.add_batch(db_session, summarised, seq=9, skew_ms=0, samples=_samples(5), at=old)
    _, fresh = await _finished(db_session, seconds=0)
    await repository.set_status(db_session, fresh, status="failed", at=T0)
    await nonverbal.add_batch(db_session, fresh, seq=0, skew_ms=0, samples=_samples(5), at=T0)
    _, running = await _finished(db_session, seconds=0)
    await repository.set_status(db_session, running, status="running", at=T0)
    await nonverbal.add_batch(db_session, running, seq=0, skew_ms=0, samples=_samples(5), at=old)

    assert await service_nonverbal.sweep_orphan_batches(opener_for(db_session), now=T0) == 2
    held = [await nonverbal.has_batches(db_session, i) for i in (abandoned, summarised, fresh, running)]
    assert held == [False, False, True, True]


async def test_an_organisation_that_switched_the_feature_off_loses_the_batches_without_a_model_call(
    db_session,
):
    from app.features.tenancy import repository as tenancy_repo

    user, attempt_id = await _finished(db_session, seconds=70)
    org = await tenancy_repo.create_organization(db_session, slug=f"nv-{uuid.uuid4().hex[:6]}", name="NV")
    await db_session.execute(
        text("UPDATE attempts SET kind = 'self_practice', org_id = :o WHERE id = :i"),
        {"o": org.id, "i": attempt_id},
    )
    db_session.expire_all()
    summariser = FakeTranscriptSummariser(payload=PAYLOAD)
    assert await _summarise(db_session, attempt_id, summariser) is False
    assert summariser.calls == []
    assert await nonverbal.summary_for(db_session, attempt_id) is None
    assert await nonverbal.has_batches(db_session, attempt_id) is False


async def test_the_export_carries_the_consent_row_and_each_attempts_summary(db_session):
    user, attempt_id = await _finished(db_session, seconds=70)
    await _summarise(db_session, attempt_id, FakeTranscriptSummariser(payload=PAYLOAD))
    consent = await service_privacy.export_nonverbal_consent_for_user(db_session, user.id)
    assert consent == {"version": "2026-11", "consented_at": T0, "withdrawn_at": None}
    (exported,) = await service_privacy.export_for_user(db_session, user.id)
    assert exported["nonverbal"]["feedback"]["summary"] == "You faced the screen most of the time."
    stranger = await identity_repo.create_user(
        db_session, email=f"nv{uuid.uuid4().hex[:8]}@example.com", name="S", password_hash=None
    )
    assert await service_privacy.export_nonverbal_consent_for_user(db_session, stranger.id) is None
