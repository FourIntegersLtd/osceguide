"""An institution granting its people access to the exams it runs.

The README promised this route from the start; only `billing` ever called
`grant`, so an institution's students had the consumer free trial and then
a paywall.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    await create_exam(client, root, code="plab")
    return org_id, admin


async def test_an_institution_grants_and_the_student_sees_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    student = await make_actor("priya@ashford.ac.uk")

    granted = await client.post(
        "/api/v1/orgs/kings/entitlements",
        json={"email": "priya@ashford.ac.uk", "exam_code": "plab", "ends_at": "2027-07-31T00:00:00Z"},
        headers=bearer(admin),
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["source"] == "org_grant"
    assert granted.json()["live"] is True

    mine = await client.get("/api/v1/me/entitlements", headers=bearer(student))
    assert [(e["exam_code"], e["source"], e["live"]) for e in mine.json()["items"]] == [
        ("plab", "org_grant", True)
    ]

    listed = await client.get("/api/v1/orgs/kings/entitlements", headers=bearer(admin))
    assert [e["id"] for e in listed.json()["items"]] == [granted.json()["id"]]


async def test_org_entitlements_can_be_searched_by_grantee_or_exam_code(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await make_actor("priya@ashford.ac.uk")
    await make_actor("other@ashford.ac.uk")
    root = await make_actor("root-search@osceguide.com", platform_admin=True)
    await create_exam(client, root, code="mrcp")

    priya_grant = (
        await client.post(
            "/api/v1/orgs/kings/entitlements",
            json={"email": "priya@ashford.ac.uk", "exam_code": "plab"},
            headers=bearer(admin),
        )
    ).json()
    other_grant = (
        await client.post(
            "/api/v1/orgs/kings/entitlements",
            json={"email": "other@ashford.ac.uk", "exam_code": "mrcp"},
            headers=bearer(admin),
        )
    ).json()

    by_email = await client.get(
        "/api/v1/orgs/kings/entitlements", params={"search": "priya"}, headers=bearer(admin)
    )
    assert [e["id"] for e in by_email.json()["items"]] == [priya_grant["id"]]

    by_exam_code = await client.get(
        "/api/v1/orgs/kings/entitlements", params={"search": "mrcp"}, headers=bearer(admin)
    )
    assert [e["id"] for e in by_exam_code.json()["items"]] == [other_grant["id"]]

    no_match = await client.get(
        "/api/v1/orgs/kings/entitlements", params={"search": "nobody-like-this"}, headers=bearer(admin)
    )
    assert no_match.json()["items"] == []
    assert no_match.json()["next_cursor"] is None


async def test_a_grant_can_be_withdrawn_and_stays_on_record(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    student = await make_actor("leaver@ashford.ac.uk")
    granted = (
        await client.post(
            "/api/v1/orgs/kings/entitlements",
            json={"email": "leaver@ashford.ac.uk", "exam_code": "plab"},
            headers=bearer(admin),
        )
    ).json()

    revoked = await client.post(
        f"/api/v1/orgs/kings/entitlements/{granted['id']}/revoke", headers=bearer(admin)
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["live"] is False
    assert revoked.json()["revoked_at"] is not None

    mine = (await client.get("/api/v1/me/entitlements", headers=bearer(student))).json()["items"]
    assert [e["live"] for e in mine] == [False]


async def test_granting_to_nobody_and_to_no_exam_are_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    nobody = await client.post(
        "/api/v1/orgs/kings/entitlements",
        json={"email": "ghost@ashford.ac.uk", "exam_code": "plab"},
        headers=bearer(admin),
    )
    assert nobody.status_code == 404
    assert nobody.json()["code"] == "user_not_found"

    await make_actor("real@ashford.ac.uk")
    no_exam = await client.post(
        "/api/v1/orgs/kings/entitlements",
        json={"email": "real@ashford.ac.uk", "exam_code": "nope"},
        headers=bearer(admin),
    )
    assert no_exam.status_code == 404
    assert no_exam.json()["code"] == "unknown_exam"


async def test_another_organisation_cannot_revoke_a_grant(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    _, other = await org_with_admin(client, make_actor, slug="guys")
    await make_actor("shared@ashford.ac.uk")
    granted = (
        await client.post(
            "/api/v1/orgs/kings/entitlements",
            json={"email": "shared@ashford.ac.uk", "exam_code": "plab"},
            headers=bearer(admin),
        )
    ).json()
    response = await client.post(
        f"/api/v1/orgs/guys/entitlements/{granted['id']}/revoke", headers=bearer(other)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "entitlement_not_found"


async def test_a_supervisor_may_not_grant(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await org_with_admin(client, make_actor)
    supervisor = await make_actor(
        "sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    response = await client.post(
        "/api/v1/orgs/kings/entitlements",
        json={"email": "sup@example.com", "exam_code": "plab"},
        headers=bearer(supervisor),
    )
    assert response.status_code == 403
