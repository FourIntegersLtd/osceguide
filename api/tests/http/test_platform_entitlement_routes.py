"""The support view of entitlements: revoking a grant, and that granting outright is gone."""

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


async def test_staff_can_no_longer_grant_or_extend_access_outright(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Access is only given by choosing a plan in Billing; the old grant and extend routes are gone."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await ensure_exam(db_session, "sca")
    _, user_id = await aged_account(client, make_actor, db_session, "nogrant@example.com")
    granted = await client.post(
        f"/api/v1/platform/users/{user_id}/entitlements",
        json={"exam_code": "sca", "note": "x"},
        headers=bearer(root),
    )
    assert granted.status_code == 404
    listed = await client.get(f"/api/v1/platform/users/{user_id}/entitlements", headers=bearer(root))
    assert listed.status_code == 404
    extended = await client.patch(
        f"/api/v1/platform/entitlements/{uuid.uuid4()}", json={"ends_at": None}, headers=bearer(root)
    )
    assert extended.status_code == 404


async def test_a_grant_can_be_revoked_and_twice_is_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    exam = await ensure_exam(db_session, "sca")
    token, user_id = await aged_account(client, make_actor, db_session, "renew@example.com")
    old_admin_grant = await ent_repo.grant(
        db_session, user_id=user_id, exam_id=exam.id, source="admin", source_ref="admin:old"
    )
    entitlement_id = str(old_admin_grant.id)
    await db_session.commit()
    assert await try_attempt(client, token) == 201

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

    missing = await client.post(
        f"/api/v1/platform/entitlements/{uuid.uuid4()}/revoke", json={"reason": "x"}, headers=bearer(root)
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "entitlement_not_found"
