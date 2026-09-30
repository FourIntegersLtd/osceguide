"""An institution or partner giving people, with or without an account, an exam to practise.

The port of b2b's practice users. Each test calls the routes the way the admin screen and
the invited person do, and checks the one gate that matters: whether the person may open
the exam's library (`GET /stations?exam_code=`), which refuses `not_entitled` without a
live grant.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.notifications.models import OutboundMessage
from app.features.tenancy.models import AuditEntry
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

PASSWORD = "Str0ng-Passw0rd!"


async def partner_with_admin(client: AsyncClient, make_actor, slug: str = "medrev"):  # type: ignore[no-untyped-def]
    """An organisation, its owner's token, and a published platform exam it has imported."""
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": "MedRevise Partners", "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    exam = await create_exam(client, root, code="plab", name="PLAB 2")
    imported = await client.post(
        f"/api/v1/orgs/{slug}/exams/import", json={"platform_exam_id": exam["id"]}, headers=bearer(admin)
    )
    assert imported.status_code == 201, imported.text
    return org_id, admin, exam["id"]


async def registered(client: AsyncClient, email: str) -> str:
    """Someone who signed up for themselves, as the consumer site does it; their access token."""
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "name": "Existing Account", "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["access_token"])


async def queued(db_session: AsyncSession, template_key: str) -> list[OutboundMessage]:
    """The emails waiting in the outbox under one template."""
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == template_key)
    return list((await db_session.execute(stmt)).scalars())


async def may_open(client: AsyncClient, token: str, exam_code: str = "plab") -> int:
    """The status the exam's library answers this person with: 200 open, 403 refused."""
    return (await client.get(f"/api/v1/stations?exam_code={exam_code}", headers=bearer(token))).status_code


async def test_an_invited_person_registers_and_the_access_is_live(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Invite by an address with no account, accept the emailed link, sign in, practise."""
    _, admin, exam_id = await partner_with_admin(client, make_actor)

    granted = await client.post(
        "/api/v1/orgs/medrev/practice-access",
        json={"email": " New.Doctor@Example.com ", "exam_id": exam_id},
        headers=bearer(admin),
    )
    assert granted.status_code == 201, granted.text
    item = granted.json()["item"]
    assert {
        key: item[key] for key in ("email", "exam_id", "exam_code", "exam_title", "status", "revoked_at")
    } == {
        "email": "new.doctor@example.com",
        "exam_id": exam_id,
        "exam_code": "plab",
        "exam_title": "PLAB 2",
        "status": "invited",
        "revoked_at": None,
    }
    assert item["user_id"] is not None

    invitations = await queued(db_session, "practice_access_invitation")
    assert [message.recipient for message in invitations] == ["new.doctor@example.com"]
    assert invitations[0].payload["exam_title"] == "PLAB 2"
    assert invitations[0].payload["invited_to"] == "MedRevise Partners"
    assert await queued(db_session, "practice_access_granted") == []
    # Read before the refused login below, which rolls the test's session back.
    invitation_token = invitations[0].payload["token"]

    # The account exists but cannot be signed into until the link is used.
    locked = await client.post(
        "/api/v1/auth/login", json={"email": "new.doctor@example.com", "password": PASSWORD}
    )
    assert locked.status_code == 401

    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": invitation_token, "password": PASSWORD},
    )
    assert confirmed.status_code in (200, 204), confirmed.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": "new.doctor@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    mine = await client.get("/api/v1/me/entitlements", headers=bearer(token))
    assert [(row["exam_code"], row["source"], row["live"]) for row in mine.json()["items"]] == [
        ("plab", "org_grant", True)
    ]
    assert await may_open(client, token) == 200

    listed = await client.get("/api/v1/orgs/medrev/practice-access", headers=bearer(admin))
    assert [(row["email"], row["status"]) for row in listed.json()["items"]] == [
        ("new.doctor@example.com", "active")
    ]


async def test_an_existing_account_is_granted_and_told(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, exam_id = await partner_with_admin(client, make_actor)
    student = await registered(client, "priya@example.com")
    assert await may_open(client, student) == 403

    granted = await client.post(
        "/api/v1/orgs/medrev/practice-access",
        json={"email": "priya@example.com", "exam_id": exam_id},
        headers=bearer(admin),
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["item"]["status"] == "active"
    assert await may_open(client, student) == 200

    told = await queued(db_session, "practice_access_granted")
    assert [(message.recipient, message.payload) for message in told] == [
        ("priya@example.com", {"exam_title": "PLAB 2", "granted_by": "MedRevise Partners"})
    ]
    audit = (await db_session.execute(select(AuditEntry.action))).scalars().all()
    assert "practice_access.granted" in audit
    assert "exam.imported" in audit

    # Granting the same exam again is a conflict and sends nothing more.
    again = await client.post(
        "/api/v1/orgs/medrev/practice-access",
        json={"email": "priya@example.com", "exam_id": exam_id},
        headers=bearer(admin),
    )
    assert again.status_code == 409
    assert again.json()["code"] == "practice_access_exists"


async def test_revoking_closes_the_gate(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin, exam_id = await partner_with_admin(client, make_actor)
    student = await registered(client, "leaver@example.com")
    access_id = (
        await client.post(
            "/api/v1/orgs/medrev/practice-access",
            json={"email": "leaver@example.com", "exam_id": exam_id},
            headers=bearer(admin),
        )
    ).json()["item"]["access_id"]
    assert await may_open(client, student) == 200

    revoked = await client.post(
        f"/api/v1/orgs/medrev/practice-access/{access_id}/revoke", headers=bearer(admin)
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["item"]["status"] == "revoked"
    assert revoked.json()["item"]["revoked_at"] is not None

    refused = await client.get("/api/v1/stations?exam_code=plab", headers=bearer(student))
    assert refused.status_code == 403
    assert refused.json()["code"] == "not_entitled"

    # The row stays on record, and revoking again answers the same row.
    listed = (await client.get("/api/v1/orgs/medrev/practice-access", headers=bearer(admin))).json()["items"]
    assert [(row["access_id"], row["status"]) for row in listed] == [(access_id, "revoked")]
    twice = await client.post(
        f"/api/v1/orgs/medrev/practice-access/{access_id}/revoke", headers=bearer(admin)
    )
    assert twice.json()["item"]["revoked_at"] == revoked.json()["item"]["revoked_at"]

    # And a fresh grant after a revoke is allowed.
    regranted = await client.post(
        "/api/v1/orgs/medrev/practice-access",
        json={"email": "leaver@example.com", "exam_id": exam_id},
        headers=bearer(admin),
    )
    assert regranted.status_code == 201
    assert await may_open(client, student) == 200


async def test_another_organisation_cannot_see_grant_or_revoke(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin, exam_id = await partner_with_admin(client, make_actor)
    _, other_admin, _ = await partner_with_admin(client, make_actor, slug="rival")
    await registered(client, "shared@example.com")
    access_id = (
        await client.post(
            "/api/v1/orgs/medrev/practice-access",
            json={"email": "shared@example.com", "exam_id": exam_id},
            headers=bearer(admin),
        )
    ).json()["item"]["access_id"]

    assert (await client.get("/api/v1/orgs/rival/practice-access", headers=bearer(other_admin))).json() == {
        "items": []
    }
    foreign_revoke = await client.post(
        f"/api/v1/orgs/rival/practice-access/{access_id}/revoke", headers=bearer(other_admin)
    )
    assert foreign_revoke.status_code == 404
    assert foreign_revoke.json()["code"] == "entitlement_not_found"
    wrong_workspace = await client.get("/api/v1/orgs/medrev/practice-access", headers=bearer(other_admin))
    assert wrong_workspace.status_code == 403


async def test_only_exams_the_organisation_offers_are_grantable(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A platform exam the organisation has not imported is refused, as is another's own exam."""
    root = await make_actor("root-extra@osceguide.com", platform_admin=True)
    not_imported = await create_exam(client, root, code="casc")
    _, admin, _ = await partner_with_admin(client, make_actor)
    _, other_admin, _ = await partner_with_admin(client, make_actor, slug="rival")
    rival_exam = await create_exam_for_org(client, other_admin, slug="rival")

    for exam_id in (not_imported["id"], rival_exam, str(uuid.uuid4())):
        refused = await client.post(
            "/api/v1/orgs/medrev/practice-access",
            json={"email": "someone@example.com", "exam_id": exam_id},
            headers=bearer(admin),
        )
        assert refused.status_code == 404, exam_id
        assert refused.json()["code"] == "unknown_exam"

    bad_email = await client.post(
        "/api/v1/orgs/medrev/practice-access",
        json={"email": "not-an-address", "exam_id": not_imported["id"]},
        headers=bearer(admin),
    )
    assert bad_email.status_code == 422
    assert bad_email.json()["code"] == "invalid_email"


async def test_a_supervisor_may_not_grant(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, _, exam_id = await partner_with_admin(client, make_actor)
    supervisor = await make_actor(
        "sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="medrev", role="supervisor"),),
        active_org_slug="medrev",
    )
    response = await client.post(
        "/api/v1/orgs/medrev/practice-access",
        json={"email": "sup@example.com", "exam_id": exam_id},
        headers=bearer(supervisor),
    )
    assert response.status_code == 403


async def test_a_bulk_grant_reports_each_row(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin, exam_id = await partner_with_admin(client, make_actor)
    await registered(client, "has.account@example.com")

    response = await client.post(
        "/api/v1/orgs/medrev/practice-access/bulk",
        json={
            "rows": [
                {"email": "has.account@example.com", "exam_id": exam_id},
                {"email": "brand.new@example.com", "exam_id": exam_id},
                {"email": "has.account@example.com", "exam_id": exam_id},
                {"email": "email", "exam_id": exam_id},
                {"email": "someone@example.com", "exam_id": "not-a-uuid"},
                {"email": "someone@example.com", "exam_id": str(uuid.uuid4())},
            ]
        },
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "results": [
            {"email": "has.account@example.com", "outcome": "granted"},
            {"email": "brand.new@example.com", "outcome": "invited"},
            {"email": "has.account@example.com", "outcome": "already_active"},
            {"email": "email", "outcome": "invalid_email"},
            {"email": "someone@example.com", "outcome": "unknown_exam"},
            {"email": "someone@example.com", "outcome": "unknown_exam"},
        ]
    }
    assert [message.recipient for message in await queued(db_session, "practice_access_invitation")] == [
        "brand.new@example.com"
    ]
    assert [message.recipient for message in await queued(db_session, "practice_access_granted")] == [
        "has.account@example.com"
    ]
    listed = (await client.get("/api/v1/orgs/medrev/practice-access", headers=bearer(admin))).json()["items"]
    assert sorted((row["email"], row["status"]) for row in listed) == [
        ("brand.new@example.com", "invited"),
        ("has.account@example.com", "active"),
    ]


async def test_a_bulk_grant_needs_one_to_five_hundred_rows(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin, exam_id = await partner_with_admin(client, make_actor)
    empty = await client.post(
        "/api/v1/orgs/medrev/practice-access/bulk", json={"rows": []}, headers=bearer(admin)
    )
    assert empty.status_code == 422
    too_many = await client.post(
        "/api/v1/orgs/medrev/practice-access/bulk",
        json={"rows": [{"email": f"person{index}@example.com", "exam_id": exam_id} for index in range(501)]},
        headers=bearer(admin),
    )
    assert too_many.status_code == 422


async def create_exam_for_org(client: AsyncClient, admin: str, *, slug: str) -> str:
    """An organisation's own published exam, marked against a platform rubric it may read."""
    root = await client.get("/api/v1/orgs/" + slug + "/exams", headers=bearer(admin))
    platform_exam = next(exam for exam in root.json()["items"] if exam["code"] == "plab")
    created = await client.post(
        f"/api/v1/orgs/{slug}/exams",
        json={
            "code": "finals",
            "name": "Rival finals",
            "default_reading_seconds": 90,
            "default_simulation_seconds": 600,
            "rubric_version_id": platform_exam["rubric_version_id"],
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"/api/v1/orgs/{slug}/exams/{created.json()['id']}/publish", headers=bearer(admin)
    )
    assert published.status_code == 200, published.text
    return str(created.json()["id"])
