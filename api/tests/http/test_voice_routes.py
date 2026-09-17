"""Issuing a join token, and what it is asked to grant."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeVoiceTokens
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def voice_tokens(client: AsyncClient) -> FakeVoiceTokens:
    """Replace the LiveKit adapter with a recording fake.

    An override rather than a patch, so the seam is the one production uses.
    """
    from app.features.voice.service import get_voice_tokens

    fake = FakeVoiceTokens()
    client._transport.app.dependency_overrides[get_voice_tokens] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def an_attempt(
    client: AsyncClient, db_session: AsyncSession, make_actor, email: str
) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    token = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    await ent_repo.grant(
        session=db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await db_session.flush()
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    return created.json()["id"], token


async def test_a_token_is_issued_for_your_own_attempt(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    attempt_id, token = await an_attempt(client, db_session, make_actor, "v1@example.com")
    response = await client.post(f"/api/v1/attempts/{attempt_id}/voice-token", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["room"] == f"attempt_{attempt_id}"


async def test_the_worker_is_given_three_strings_and_no_more(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """Everything else it fetches from the bootstrap route, so the dispatch
    payload cannot become a second copy of the attempt, free to drift."""
    attempt_id, token = await an_attempt(client, db_session, make_actor, "v2@example.com")
    await client.post(f"/api/v1/attempts/{attempt_id}/voice-token", headers=bearer(token))

    metadata = voice_tokens.issued[0]["dispatch_metadata"]
    assert set(metadata) == {"attempt_id", "backend", "candidate_ref"}  # type: ignore[arg-type]
    assert metadata["attempt_id"] == attempt_id  # type: ignore[index]


async def test_the_agent_name_reflects_family_and_mode(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    attempt_id, token = await an_attempt(client, db_session, make_actor, "v3@example.com")
    await client.post(f"/api/v1/attempts/{attempt_id}/voice-token", headers=bearer(token))
    assert voice_tokens.issued[0]["agent_name"] == "assessment-self-hosted"


async def test_the_response_carries_no_dispatch_detail(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """The browser has no use for the agent name or the backend label; b2c
    hands it a metadata blob it only passes back."""
    attempt_id, token = await an_attempt(client, db_session, make_actor, "v4@example.com")
    response = await client.post(f"/api/v1/attempts/{attempt_id}/voice-token", headers=bearer(token))
    assert set(response.json()) == {"token", "server_url", "room", "attempt_id"}


async def test_someone_elses_attempt_is_refused(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    attempt_id, _ = await an_attempt(client, db_session, make_actor, "v5@example.com")
    stranger = await make_actor("v5-stranger@example.com")
    response = await client.post(f"/api/v1/attempts/{attempt_id}/voice-token", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "attempt_not_yours"


async def test_a_finished_attempt_cannot_be_rejoined(
    client: AsyncClient, db_session: AsyncSession, make_actor, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    from app.features.attempts import repository as attempts_repo

    attempt_id, token = await an_attempt(client, db_session, make_actor, "v6@example.com")
    await attempts_repo.set_status(
        db_session, uuid.UUID(attempt_id), status="evaluated", at=datetime.now(UTC)
    )
    await db_session.flush()
    response = await client.post(f"/api/v1/attempts/{attempt_id}/voice-token", headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "attempt_not_joinable"
