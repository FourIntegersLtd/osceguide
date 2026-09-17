"""Creating and reading attempts, and the entitlement gate in front of them."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
async def an_exam_to_attempt(db_session: AsyncSession) -> None:
    """Every test here names an exam, and nothing is seeded any more."""
    await ensure_exam(db_session, "sca")


async def entitle(session: AsyncSession, token_user: uuid.UUID, code: str = "sca") -> None:
    exam = await ensure_exam(session, code)
    assert exam is not None
    await ent_repo.grant(
        session,
        user_id=token_user,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await session.flush()


async def test_starting_an_attempt_needs_an_entitlement(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """No entitlement and no trial left is a refusal.

    This used to pass with a brand-new account, because the free trial was
    never consulted — `trial=None` made `decide` skip the branch. A new account
    is exactly the case that *should* be allowed, so the account is aged past
    the trial window to test what this was always meant to test.
    """
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("nopay@example.com")
    await db_session.execute(
        update(User)
        .where(User.email == "nopay@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()

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


# --------------------------------------------------------------------------
# The free trial (E1/E2)
# --------------------------------------------------------------------------


async def test_a_new_user_gets_the_free_trial(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`trial_available` was written, unit-tested, and never given a trial to test.

    `attempts.service` passed `trial=None`, and `decide` skips the trial branch
    entirely when it is None — so a brand-new account with no entitlement was
    refused outright and nobody could try the product.
    """
    token = await make_actor("trialist@example.com")

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert response.status_code == 201, response.text


async def test_the_trial_runs_out_after_three_attempts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Three, counted the legacy way. Ported verbatim as the oracle."""
    from app.features.attempts import repository as attempts_repo
    from app.features.identity import repository as identity_repo

    token = await make_actor("threeonly@example.com")
    user = await identity_repo.user_by_email(db_session, "threeonly@example.com")
    assert user is not None

    for _ in range(3):
        created = await client.post(
            "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
        )
        assert created.status_code == 201, created.text
        attempt_id = uuid.UUID(created.json()["id"])
        await attempts_repo.set_status(db_session, attempt_id, status="running", at=NOW)
        await attempts_repo.set_status(db_session, attempt_id, status="interaction_complete", at=NOW)
    await db_session.flush()

    refused = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "not_entitled"
    assert refused.json()["details"]["reason"] == "trial_exhausted"


async def test_an_old_account_has_no_trial_left(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Fourteen days, and the comparison is strict: a fifteen-day-old account is out."""
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("veteran@example.com")
    await db_session.execute(
        update(User)
        .where(User.email == "veteran@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=15))
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert response.status_code == 403, response.text
    assert response.json()["details"]["reason"] == "trial_exhausted"


# --------------------------------------------------------------------------
# Abandoning
# --------------------------------------------------------------------------


async def an_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession, email: str
) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    token = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await entitle(db_session, user.id)
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    return token, created.json()["id"]


async def test_a_candidate_can_walk_away_from_an_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Without this an abandoned attempt stays `running` forever.

    It holds the slot's one live attempt, so a re-dispatch is the only way out,
    and every screen that reads status counts it as in progress.
    """
    token, attempt_id = await an_attempt(client, make_actor, db_session, "quitter@example.com")

    response = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"

    read_back = await client.get(f"/api/v1/attempts/{attempt_id}", headers=bearer(token))
    assert read_back.json()["status"] == "failed"


async def test_an_attempt_already_finished_cannot_be_abandoned(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """There is a transcript being marked; throwing it away is not a candidate's to do."""
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts.domain import Status

    token, attempt_id = await an_attempt(client, make_actor, db_session, "done@example.com")
    await attempts_repo.set_status(
        db_session, uuid.UUID(attempt_id), status=Status.RUNNING, at=datetime.now(UTC)
    )
    await attempts_repo.set_status(
        db_session,
        uuid.UUID(attempt_id),
        status=Status.INTERACTION_COMPLETE,
        at=datetime.now(UTC),
    )
    await db_session.flush()

    response = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_attempt_state"


async def test_abandoning_twice_is_refused_rather_than_silently_accepted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token, attempt_id = await an_attempt(client, make_actor, db_session, "twice@example.com")
    await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    again = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    assert again.status_code == 409
    assert again.json()["code"] == "invalid_attempt_state"


async def test_abandoning_someone_elses_attempt_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, attempt_id = await an_attempt(client, make_actor, db_session, "mine@example.com")
    stranger = await make_actor("notmine@example.com")
    response = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "attempt_not_yours"
