"""Creating and reading attempts, and the entitlement gate in front of them."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog import repository as catalog_repo
from app.features.entitlements import repository as ent_repo
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


async def entitle(session: AsyncSession, token_user: uuid.UUID, code: str = "sca") -> None:
    exam = await catalog_repo.exam_by_code(session, code)
    assert exam is not None
    await ent_repo.grant(
        session,
        user_id=token_user,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await session.flush()


async def test_starting_an_attempt_needs_an_entitlement(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("nopay@example.com")
    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert response.status_code == 403
    assert response.json()["code"] == "not_entitled"


async def test_an_entitled_user_may_start_an_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("paid@example.com")
    from app.features.identity import repository as identity_repo

    user = await identity_repo.user_by_email(db_session, "paid@example.com")
    assert user is not None
    await entitle(db_session, user.id)

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert response.json()["kind"] == "practice"


async def test_an_unknown_exam_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("x@example.com")
    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "mrcp"}, headers=bearer(token)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_reading_someone_elses_attempt_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    owner_token = await make_actor("owner@example.com")
    owner = await identity_repo.user_by_email(db_session, "owner@example.com")
    assert owner is not None
    await entitle(db_session, owner.id)
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(owner_token)
    )
    attempt_id = created.json()["id"]

    stranger = await make_actor("stranger@example.com")
    response = await client.get(f"/api/v1/attempts/{attempt_id}", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "attempt_not_yours"


async def test_an_owner_reads_their_own_attempt_and_transcript(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    token = await make_actor("me@example.com")
    user = await identity_repo.user_by_email(db_session, "me@example.com")
    assert user is not None
    await entitle(db_session, user.id)
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    attempt_id = created.json()["id"]

    assert (await client.get(f"/api/v1/attempts/{attempt_id}", headers=bearer(token))).status_code == 200
    transcript = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(token))
    assert transcript.status_code == 200
    assert transcript.json()["messages"] == []
    results = await client.get(f"/api/v1/attempts/{attempt_id}/result", headers=bearer(token))
    assert results.json()["items"] == []


async def test_my_entitlements_are_listed(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    token = await make_actor("list@example.com")
    user = await identity_repo.user_by_email(db_session, "list@example.com")
    assert user is not None
    await entitle(db_session, user.id)
    response = await client.get("/api/v1/me/entitlements", headers=bearer(token))
    assert response.status_code == 200
    assert [e["exam_code"] for e in response.json()["items"]] == ["sca"]
    assert response.json()["items"][0]["live"] is True
