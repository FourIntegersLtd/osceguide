"""The support view of entitlements: every grant a person has ever held."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_the_console_sees_every_grant_with_its_source_and_whether_it_is_live(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    person = await identity_repo.create_user(
        db_session, email="paid@example.com", name="P", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    lapsed = await ent_repo.grant(
        db_session,
        user_id=person.id,
        exam_id=exam.id,
        source="purchase",
        source_ref="pi_old",
        ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    live = await ent_repo.grant(
        db_session, user_id=person.id, exam_id=exam.id, source="admin", source_ref="admin:x"
    )
    await db_session.flush()

    listed = await client.get(f"/api/v1/platform/users/{person.id}/entitlements", headers=bearer(root))
    assert listed.status_code == 200, listed.text
    rows = {row["id"]: row for row in listed.json()["items"]}
    assert rows[str(lapsed.id)]["live"] is False
    assert rows[str(lapsed.id)]["source_ref"] == "pi_old"
    assert rows[str(live.id)]["live"] is True
    assert rows[str(live.id)]["source"] == "admin"
    assert rows[str(live.id)]["exam_code"] == "sca"


async def test_an_unknown_account_is_404_and_a_non_admin_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    someone = await make_actor("someone@example.com")
    missing = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/entitlements", headers=bearer(root))
    assert missing.status_code == 404
    assert missing.json()["code"] == "user_not_found"
    refused = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/entitlements", headers=bearer(someone))
    assert refused.status_code == 403


async def aged_account(client: AsyncClient, make_actor, db_session: AsyncSession, email: str):  # type: ignore[no-untyped-def]
    """A person whose free trial has run out, so only a grant lets them in."""
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor(email)
    await db_session.execute(
        update(User).where(User.email == email).values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    # Released to the outer transaction the way a successful request would be:
    # the first request this person makes is a refusal, and the harness rolls
    # a refused request back to the last release, which would take them too.
    await db_session.commit()
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    return token, user.id


async def try_attempt(client: AsyncClient, token: str) -> int:
    started = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    return started.status_code


async def test_a_platform_grant_opens_the_exam_and_is_idempotent(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    token, user_id = await aged_account(client, make_actor, db_session, "lapsed@example.com")
    assert await try_attempt(client, token) == 403

    body = {"exam_code": "sca", "ends_at": "2027-01-01T00:00:00Z", "note": "paid under another address"}
    granted = await client.post(
        f"/api/v1/platform/users/{user_id}/entitlements", json=body, headers=bearer(root)
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["source"] == "admin"
    assert granted.json()["live"] is True
    assert granted.json()["granted_by"] is not None
    assert await try_attempt(client, token) == 201

    again = await client.post(
        f"/api/v1/platform/users/{user_id}/entitlements", json=body, headers=bearer(root)
    )
    assert again.status_code == 201
    assert again.json()["id"] == granted.json()["id"], "a double-click must not grant twice"
    listed = await client.get(f"/api/v1/platform/users/{user_id}/entitlements", headers=bearer(root))
    assert len(listed.json()["items"]) == 1

    audit = await client.get("/api/v1/platform/audit?action=entitlement.granted", headers=bearer(root))
    [row] = audit.json()["items"]
    assert row["target_id"] == granted.json()["id"]
    assert row["meta"]["note"] == "paid under another address"
    assert row["org_id"] is None


async def test_a_grant_can_be_extended_and_then_revoked(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    token, user_id = await aged_account(client, make_actor, db_session, "renew@example.com")
    granted = await client.post(
        f"/api/v1/platform/users/{user_id}/entitlements",
        json={"exam_code": "sca", "ends_at": "2026-10-01T00:00:00Z", "note": "one month"},
        headers=bearer(root),
    )
    entitlement_id = granted.json()["id"]

    extended = await client.patch(
        f"/api/v1/platform/entitlements/{entitlement_id}",
        json={"ends_at": "2026-12-01T00:00:00Z", "note": "renewed by bank transfer"},
        headers=bearer(root),
    )
    assert extended.status_code == 200, extended.text
    assert extended.json()["ends_at"].startswith("2026-12-01")
    assert extended.json()["id"] == entitlement_id, "a renewal is the same row"
    same = await client.patch(
        f"/api/v1/platform/entitlements/{entitlement_id}",
        json={"ends_at": "2026-12-01T00:00:00Z"},
        headers=bearer(root),
    )
    assert same.status_code == 200
    extensions = await client.get("/api/v1/platform/audit?action=entitlement.extended", headers=bearer(root))
    assert len(extensions.json()["items"]) == 1, "an unchanged end date is not an extension"
    assert extensions.json()["items"][0]["meta"]["to"].startswith("2026-12-01")

    revoked = await client.post(
        f"/api/v1/platform/entitlements/{entitlement_id}/revoke",
        json={"reason": "refunded"},
        headers=bearer(root),
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["live"] is False
    assert revoked.json()["revoked_at"] is not None
    assert await try_attempt(client, token) == 403
    twice = await client.post(
        f"/api/v1/platform/entitlements/{entitlement_id}/revoke",
        json={"reason": "refunded"},
        headers=bearer(root),
    )
    assert twice.json()["revoked_at"] == revoked.json()["revoked_at"]
    revocations = await client.get("/api/v1/platform/audit?action=entitlement.revoked", headers=bearer(root))
    assert len(revocations.json()["items"]) == 1


async def test_a_grant_for_an_unknown_exam_or_person_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, user_id = await aged_account(client, make_actor, db_session, "who@example.com")
    unknown_exam = await client.post(
        f"/api/v1/platform/users/{user_id}/entitlements",
        json={"exam_code": "mrcp", "note": "x"},
        headers=bearer(root),
    )
    assert unknown_exam.status_code == 404
    assert unknown_exam.json()["code"] == "unknown_exam"
    nobody = await client.post(
        f"/api/v1/platform/users/{uuid.uuid4()}/entitlements",
        json={"exam_code": "sca", "note": "x"},
        headers=bearer(root),
    )
    assert nobody.status_code == 404
    missing = await client.patch(
        f"/api/v1/platform/entitlements/{uuid.uuid4()}", json={"ends_at": None}, headers=bearer(root)
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "entitlement_not_found"
