"""The assistant worker's contract.

Payload shapes from `livekit_assistant_worker/bootstrap.py:40-57` and
`transcript.py:55-61`. The paths are hardcoded in the worker rather than
configured, so mounting them anywhere else breaks it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.assistant import repository
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def worker_headers() -> dict[str, str]:
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


async def a_session(client: AsyncClient, make_actor, session_type: str = "help") -> str:  # type: ignore[no-untyped-def]
    token = await make_actor(f"a{uuid.uuid4().hex[:8]}@example.com")
    created = await client.post(
        "/api/v1/assistant/sessions",
        json={"session_type": session_type},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def test_bootstrap_carries_rendered_instructions(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    session_id = await a_session(client, make_actor)
    response = await client.get(f"/api/worker/assistant-sessions/{session_id}", headers=worker_headers())
    assert response.status_code == 200
    payload = response.json()["session"]
    assert payload["session_id"] == session_id
    assert payload["instructions"].strip()
    assert payload["worker_type"] == "help"


async def test_the_worker_routes_need_the_secret(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    session_id = await a_session(client, make_actor)
    assert (await client.get(f"/api/worker/assistant-sessions/{session_id}")).status_code == 401


async def test_the_legacy_persona_name_resolves_to_the_workers_own(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """b2c's records say `athena-doctor`; the worker's enum does not have it."""
    session_id = await a_session(client, make_actor, session_type="athena-doctor")
    response = await client.get(f"/api/worker/assistant-sessions/{session_id}", headers=worker_headers())
    assert response.json()["session"]["worker_type"] == "consulting-doctor"


async def test_athena_doctor_bootstrap_uses_station_context(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The station reaches the worker from the database, named by version id (SEC-007)."""
    _, admin = await org_with_admin(client, make_actor)
    station = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Chest pain",
            "exam_code": "sca",
            "content": {
                "station_patient_name": "Sam Green",
                "station_patient_biodata": "Sam Green, 54",
                "doctor_task": "Assess chest pain in primary care.",
                "patient_information": ["Central chest tightness for 20 minutes"],
                "ice": ["Worried this is a heart attack"],
                "management_points": ["Explore red flags", "Safety-net clearly"],
            },
        },
        headers=bearer(admin),
    )
    assert station.status_code == 201, station.text
    published = await client.post(
        f"/api/v1/orgs/kings/stations/{station.json()['id']}/versions/1/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    created = await client.post(
        "/api/v1/assistant/sessions",
        json={"session_type": "athena-doctor", "station_version_id": published.json()["id"]},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text

    response = await client.get(
        f"/api/worker/assistant-sessions/{created.json()['id']}", headers=worker_headers()
    )
    payload = response.json()["session"]
    assert payload["worker_type"] == "consulting-doctor"
    assert "Chest pain" in payload["instructions"]
    assert "The learner is role-playing the patient" in payload["instructions"]
    assert "Central chest tightness" in payload["instructions"]


async def test_an_unknown_session_type_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("unknown@example.com")
    response = await client.post(
        "/api/v1/assistant/sessions", json={"session_type": "chatbot"}, headers=bearer(token)
    )
    assert response.status_code == 422
    assert response.json()["code"] == "unknown_assistant_type"


async def test_a_help_transcript_is_kept(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    session_id = await a_session(client, make_actor, session_type="help")
    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/transcript",
        json={
            "session_id": session_id,
            "worker_type": "help",
            "candidate_ref": "c",
            "transcript": {
                "messages": [{"message_id": "m0", "seq": 0, "role": "user", "message": "How do I start?"}]
            },
        },
        headers=worker_headers(),
    )
    assert response.status_code == 202
    stored = await repository.messages_for(db_session, uuid.UUID(session_id))
    assert [m.message for m in stored] == ["How do I start?"]


async def test_a_navigation_transcript_keeps_nothing(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """Navigation, not conversation. Keeping it would collect recordings of
    people's screens for nothing."""
    session_id = await a_session(client, make_actor, session_type="onboarding")
    await client.post(
        f"/api/worker/assistant-sessions/{session_id}/transcript",
        json={
            "session_id": session_id,
            "worker_type": "onboarding",
            "transcript": {"messages": [{"message_id": "m0", "seq": 0, "role": "user", "message": "hi"}]},
        },
        headers=worker_headers(),
    )
    assert await repository.messages_for(db_session, uuid.UUID(session_id)) == []


async def test_a_dashboard_transcript_is_kept_until_it_has_been_summarised(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """The turns are the only record until the note exists.

    So a dashboard transcript is stored and a summary is queued in the same
    transaction; the job writes the note and deletes the turns. Discarding here
    would lose the one thing worth keeping.
    """
    session_id = await a_session(client, make_actor, session_type="dashboard")
    await client.post(
        f"/api/worker/assistant-sessions/{session_id}/transcript",
        json={
            "session_id": session_id,
            "worker_type": "dashboard",
            "transcript": {"messages": [{"message_id": "m0", "seq": 0, "role": "user", "message": "hi"}]},
        },
        headers=worker_headers(),
    )
    stored = await repository.messages_for(db_session, uuid.UUID(session_id))
    assert [m.message for m in stored] == ["hi"]

    queued = await db_session.execute(
        text("SELECT task_name FROM procrastinate_jobs WHERE args->>'session_id' = :id"),
        {"id": session_id},
    )
    assert list(queued.scalars()) == ["summarise_assistant_session"]


async def test_a_repeated_transcript_message_is_stored_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    session_id = await a_session(client, make_actor)
    body = {
        "session_id": session_id,
        "worker_type": "help",
        "transcript": {"messages": [{"message_id": "m0", "seq": 0, "role": "user", "message": "once"}]},
    }
    url = f"/api/worker/assistant-sessions/{session_id}/transcript"
    await client.post(url, json=body, headers=worker_headers())
    await client.post(url, json=body, headers=worker_headers())
    assert len(await repository.messages_for(db_session, uuid.UUID(session_id))) == 1


async def test_completing_a_session_records_usage(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    session_id = await a_session(client, make_actor)
    response = await client.post(
        f"/api/worker/sessions/{session_id}/complete",
        json={"end_reason": "idle", "usage": {"seconds": 42}},
        headers=worker_headers(),
    )
    assert response.status_code == 202
    row = await repository.by_id(db_session, uuid.UUID(session_id))
    assert row is not None
    assert row.status == "completed"
    assert row.end_reason == "idle"


async def test_a_completed_session_cannot_be_rejoined(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    session_id = await a_session(client, make_actor)
    await client.post(f"/api/worker/sessions/{session_id}/complete", json={}, headers=worker_headers())
    response = await client.get(f"/api/worker/assistant-sessions/{session_id}", headers=worker_headers())
    assert response.status_code == 409
    assert response.json()["code"] == "assistant_session_not_joinable"
