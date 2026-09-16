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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.attempts import repository
from app.features.catalog import repository as catalog_repo
from app.features.identity import repository as identity_repo

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

DEFINITION = {
    "id": "def-1",
    "version": 1,
    "framework_id": "sca-rcgp-v1",
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
        "framework_id": "sca-rcgp-v1",
        "primary_model": "gpt-5-mini",
        "version": "platform-default@1",
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
    exam = await catalog_repo.exam_by_code(session, "sca")
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

    stored = await repository.chunks_for(db_session, attempt_id)
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

    stored = await repository.chunks_for(db_session, attempt_id)
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
    stored = await repository.chunks_for(db_session, attempt_id)
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
