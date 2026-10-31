"""The worker contract, asserted from the worker's side of it.

The payload shapes are taken from `assessment-platform`:
`livekit_assessment_worker/sinks.py` posts `{attempt_id, message}` and
`{attempt_id, transcript}`, and `bootstrap.py` validates the response as
`AssessmentAttempt` + `Scenario`, refuses empty instructions, and refuses an
attempt id other than the one it was dispatched with.

If any of this drifts, a live session fails on connect with nothing to show for
it, so these are contract tests rather than ordinary HTTP tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.attempts import repository
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import TranscriptMessage
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.rubrics import frozen_rubric

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

# The rubric an attempt is marked against is frozen onto it at render, so a
# definition without one is deliberately unmarkable. `FRAMEWORK_ID` is that
# rubric version's id, which is what everything downstream records.
RUBRIC = frozen_rubric()
FRAMEWORK_ID = str(RUBRIC["framework"]["id"])

DEFINITION = {
    "id": "def-1",
    "version": "1",
    "framework_id": FRAMEWORK_ID,
    "scenario_ref": {"source": "library", "scenario_id": "station-1"},
    "interaction_profile": {
        "mode": "patient",
        "instructions": "You are the patient. The person speaking is the doctor.",
        "greeting": "Hello doctor.",
        "tools": [],
        "tool_context": {},
        "max_tool_steps": 5,
        "runtime_hint": "pipeline",
    },
    "evaluation_policy": {
        "framework_id": FRAMEWORK_ID,
        "primary_model": "gpt-5-mini",
        "version": "platform-default@1",
        "rubric": RUBRIC,
    },
    "snapshot_at": NOW.isoformat(),
}


def worker_headers() -> dict[str, str]:
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


async def an_attempt(session: AsyncSession, *, frozen: bool = True) -> uuid.UUID:
    user = await identity_repo.create_user(
        session, email=f"c{uuid.uuid4().hex[:8]}@example.com", name="C", password_hash=None
    )
    exam = await ensure_exam(session, "sca")
    assert exam is not None
    attempt = await repository.create_attempt(
        session, kind="practice", user_id=user.id, exam_id=exam.id, room_name="unified_x"
    )
    if frozen:
        await repository.freeze_definition(session, attempt.id, definition=DEFINITION, at=NOW)
    await session.flush()
    return attempt.id


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------


async def test_a_worker_route_refuses_a_missing_secret(client: AsyncClient, db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    response = await client.get(f"/api/worker/attempts/{attempt_id}")
    assert response.status_code == 401


async def test_a_worker_route_refuses_a_wrong_secret(client: AsyncClient, db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    settings = get_settings()
    response = await client.get(
        f"/api/worker/attempts/{attempt_id}", headers={settings.worker_secret_header: "nope"}
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------
# Bootstrap
# --------------------------------------------------------------------------


async def test_bootstrap_returns_an_attempt_and_a_scenario(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    attempt_id = await an_attempt(db_session)
    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"attempt", "scenario"}
    assert body["attempt"]["attempt_id"] == str(attempt_id)


async def test_bootstrap_never_reveals_the_evaluation_policy(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The worker cannot import an evaluator, and a worker that knew how it
    would be marked could be steered by it."""
    attempt_id = await an_attempt(db_session)
    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert "evaluation_policy" not in response.json()["attempt"]["definition"]
    assert "gpt-5-mini" not in response.text


async def test_bootstrap_carries_rendered_instructions(client: AsyncClient, db_session: AsyncSession) -> None:
    """The worker refuses a job whose instructions are blank, so an empty render
    must never reach it."""
    attempt_id = await an_attempt(db_session)
    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    profile = response.json()["attempt"]["definition"]["interaction_profile"]
    assert profile["instructions"].strip()


async def test_bootstrap_of_an_unknown_attempt_is_not_found(client: AsyncClient) -> None:
    response = await client.get(f"/api/worker/attempts/{uuid.uuid4()}", headers=worker_headers())
    assert response.status_code == 404


async def test_bootstrap_before_a_definition_exists_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Better a clear error than a job that dies on connect."""
    attempt_id = await an_attempt(db_session, frozen=False)
    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert response.status_code == 409
    assert response.json()["code"] == "attempt_not_ready"


# --------------------------------------------------------------------------
# Transcript chunks
# --------------------------------------------------------------------------


def chunk(message_id: str, seq: int, role: str = "user") -> dict:
    return {
        "role": role,
        "message": f"turn {seq}",
        "timestamp": NOW.isoformat(),
        "message_id": message_id,
        "seq": seq,
    }


async def test_a_chunk_is_accepted(client: AsyncClient, db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    response = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript-chunks",
        json={"attempt_id": str(attempt_id), "message": chunk("m1", 0)},
        headers=worker_headers(),
    )
    assert response.status_code == 202


async def test_the_same_chunk_twice_is_accepted_and_stored_once(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The worker posts chunks best-effort and never reads the response, so the
    same turn genuinely arrives twice."""
    attempt_id = await an_attempt(db_session)
    body = {"attempt_id": str(attempt_id), "message": chunk("m1", 0)}
    url = f"/api/worker/attempts/{attempt_id}/transcript-chunks"
    assert (await client.post(url, json=body, headers=worker_headers())).status_code == 202
    assert (await client.post(url, json=body, headers=worker_headers())).status_code == 202

    stored = await transcripts.chunks_for(db_session, attempt_id)
    assert len(stored) == 1


async def test_a_chunk_for_a_different_attempt_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A worker may only write to the attempt it was dispatched for."""
    attempt_id = await an_attempt(db_session)
    other = await an_attempt(db_session)
    response = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript-chunks",
        json={"attempt_id": str(other), "message": chunk("m1", 0)},
        headers=worker_headers(),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "attempt_mismatch"


async def test_a_chunk_after_compaction_stores_nothing(client: AsyncClient, db_session: AsyncSession) -> None:
    """The final transcript carried every turn, so a late chunk is dropped, not stored beside the document."""
    attempt_id = await an_attempt(db_session)
    url = f"/api/worker/attempts/{attempt_id}/transcript-chunks"
    await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)},
        headers=worker_headers(),
    )
    assert await transcripts.compact(db_session, attempt_id) is True

    late = {"attempt_id": str(attempt_id), "message": chunk("late", 9)}
    assert (await client.post(url, json=late, headers=worker_headers())).status_code == 202

    assert [t.message_id for t in await transcripts.chunks_for(db_session, attempt_id)] == ["m0", "m1"]
    assert await transcripts.seen_message_ids(db_session, attempt_id) == {"m0", "m1"}
    rows = await db_session.scalar(
        select(func.count()).select_from(TranscriptMessage).where(TranscriptMessage.attempt_id == attempt_id)
    )
    assert rows == 0


async def test_a_duplicate_chunk_before_compaction_is_still_stored_once(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    attempt_id = await an_attempt(db_session)
    url = f"/api/worker/attempts/{attempt_id}/transcript-chunks"
    body = {"attempt_id": str(attempt_id), "message": chunk("m1", 1)}
    await client.post(url, json=body, headers=worker_headers())
    await client.post(url, json=body, headers=worker_headers())

    assert [t.message_id for t in await transcripts.chunks_for(db_session, attempt_id)] == ["m1"]


async def test_a_transcript_delivered_after_compaction_changes_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    attempt_id = await an_attempt(db_session)
    url = f"/api/worker/attempts/{attempt_id}/transcript"
    await client.post(
        url,
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)},
        headers=worker_headers(),
    )
    await transcripts.compact(db_session, attempt_id)

    again = await client.post(
        url,
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id, turns=5)},
        headers=worker_headers(),
    )

    assert again.status_code == 202
    assert [t.seq for t in await transcripts.chunks_for(db_session, attempt_id)] == [0, 1]
    assert await transcripts.chunk_count(db_session, attempt_id) == 2


# --------------------------------------------------------------------------
# Completed transcript
# --------------------------------------------------------------------------


def transcript(attempt_id: uuid.UUID, turns: int = 2) -> dict:
    return {
        "attempt_id": str(attempt_id),
        "messages": [chunk(f"m{i}", i, "user" if i % 2 == 0 else "assistant") for i in range(turns)],
        "complete": True,
        "runtime_label": "livekit",
    }


async def test_a_completed_transcript_is_accepted(client: AsyncClient, db_session: AsyncSession) -> None:
    attempt_id = await an_attempt(db_session)
    response = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)},
        headers=worker_headers(),
    )
    assert response.status_code == 202


async def test_delivering_twice_is_accepted_and_changes_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Delivery retries on any non-2xx, so a slow first write is redelivered."""
    attempt_id = await an_attempt(db_session)
    body = {"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)}
    url = f"/api/worker/attempts/{attempt_id}/transcript"
    assert (await client.post(url, json=body, headers=worker_headers())).status_code == 202
    assert (await client.post(url, json=body, headers=worker_headers())).status_code == 202

    stored = await transcripts.chunks_for(db_session, attempt_id)
    assert len(stored) == 2


async def test_delivery_fills_in_turns_the_chunks_missed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Chunks are best-effort, so the final transcript is the authority."""
    attempt_id = await an_attempt(db_session)
    await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript-chunks",
        json={"attempt_id": str(attempt_id), "message": chunk("m0", 0)},
        headers=worker_headers(),
    )
    await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id, turns=4)},
        headers=worker_headers(),
    )
    stored = await transcripts.chunks_for(db_session, attempt_id)
    assert [m.seq for m in stored] == [0, 1, 2, 3]


async def test_a_transcript_for_a_different_attempt_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    attempt_id = await an_attempt(db_session)
    other = await an_attempt(db_session)
    response = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(other), "transcript": transcript(other)},
        headers=worker_headers(),
    )
    assert response.status_code == 409


async def test_delivering_a_transcript_queues_the_marking(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The job is written by the same transaction as the transcript.

    This is the whole reason for a Postgres-backed queue (ADR 0006), and it is
    asserted rather than assumed: procrastinate's own connector holds a separate
    pool, so deferring through it would commit the job on another connection and
    a rolled-back transcript could still leave marking queued.
    """
    from sqlalchemy import text

    attempt_id = await an_attempt(db_session)
    # Bootstrap first: that is what starts the attempt, and the sequence a real
    # worker follows.
    await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)},
        headers=worker_headers(),
    )

    queued = (
        (
            await db_session.execute(
                text(
                    "SELECT args FROM procrastinate_jobs "
                    "WHERE task_name = 'score_attempt' AND args->>'attempt_id' = :id"
                ),
                {"id": str(attempt_id)},
            )
        )
        .scalars()
        .all()
    )
    assert len(queued) == 1
    assert queued[0]["framework_id"] == FRAMEWORK_ID


async def test_a_redelivered_transcript_does_not_queue_a_second_marking(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import text

    attempt_id = await an_attempt(db_session)
    await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    body = {"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)}
    url = f"/api/worker/attempts/{attempt_id}/transcript"
    await client.post(url, json=body, headers=worker_headers())
    await client.post(url, json=body, headers=worker_headers())

    count = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM procrastinate_jobs "
                "WHERE task_name = 'score_attempt' AND args->>'attempt_id' = :id"
            ),
            {"id": str(attempt_id)},
        )
    ).scalar_one()
    assert count == 1


async def test_bootstrapping_marks_the_attempt_running(client: AsyncClient, db_session: AsyncSession) -> None:
    """The only signal that a session began. Without it the completed transcript
    cannot move the attempt on, and the marking is never queued."""
    attempt_id = await an_attempt(db_session)
    await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    assert attempt.status == "running"
    assert attempt.started_at is not None


async def test_a_second_bootstrap_does_not_restart_the_attempt(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A worker re-reads its bootstrap after a reconnect."""
    attempt_id = await an_attempt(db_session)
    url = f"/api/worker/attempts/{attempt_id}"
    await client.get(url, headers=worker_headers())
    first = await repository.attempt_by_id(db_session, attempt_id)
    assert first is not None
    started = first.started_at

    assert (await client.get(url, headers=worker_headers())).status_code == 200
    again = await repository.attempt_by_id(db_session, attempt_id)
    assert again is not None and again.started_at == started


# --------------------------------------------------------------------------
# S-11: access that ends mid-attempt
# --------------------------------------------------------------------------


async def a_lapsed_learners_attempt(session: AsyncSession, *, status: str) -> tuple[uuid.UUID, uuid.UUID]:
    """An attempt whose owner has no grant and a trial that ended: (attempt id, user id)."""
    from datetime import timedelta

    from sqlalchemy import update

    from app.features.identity.models import User

    attempt_id = await an_attempt(session)
    attempt = await repository.attempt_by_id(session, attempt_id)
    assert attempt is not None
    await session.execute(
        update(User).where(User.id == attempt.user_id).values(created_at=NOW - timedelta(days=30))
    )
    if status != "created":
        await repository.set_status(session, attempt_id, status=status, at=NOW)
    await session.flush()
    return attempt_id, attempt.user_id


async def test_an_attempt_not_yet_started_is_refused_at_bootstrap_when_access_has_ended(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    attempt_id, _ = await a_lapsed_learners_attempt(db_session, status="created")

    response = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "not_entitled"


async def test_an_attempt_refused_at_bootstrap_is_failed_not_left_created(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    attempt_id, _ = await a_lapsed_learners_attempt(db_session, status="created")

    refused = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())

    assert refused.status_code == 403, refused.text
    attempt = await repository.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    assert (attempt.status, attempt.failed_reason) == ("failed", "not_entitled")


async def test_an_attempt_already_running_finishes_after_access_ends_but_a_new_one_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.features.attempts import service as attempts_service
    from app.features.entitlements.errors import NotEntitled

    attempt_id, user_id = await a_lapsed_learners_attempt(db_session, status="running")

    reconnect = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    turn = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript-chunks",
        json={"attempt_id": str(attempt_id), "message": chunk("m1", 0)},
        headers=worker_headers(),
    )
    submit = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)},
        headers=worker_headers(),
    )

    assert (reconnect.status_code, turn.status_code, submit.status_code) == (200, 202, 202)
    with pytest.raises(NotEntitled):
        await attempts_service.start_attempt(
            db_session, user_id=user_id, kind="practice", exam_code="sca", now=NOW
        )
