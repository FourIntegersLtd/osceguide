"""What the console does for an organisation that is in trouble.

Renewing a lapsed contract, and reaching the people inside an organisation
without becoming its administrator.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.http.test_platform_console_routes import an_org
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def with_contract(client: AsyncClient, root: str, slug: str, ends_at: datetime) -> None:
    await an_org(client, root, slug)
    patched = await client.patch(
        f"/api/v1/platform/organizations/{slug}",
        json={"contract_ends_at": ends_at.isoformat()},
        headers=bearer(root),
    )
    assert patched.status_code == 200, patched.text


async def test_the_overview_names_the_organisations_to_look_at_first(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    now = datetime.now(UTC)
    await with_contract(client, root, "ending", now + timedelta(days=10))
    await with_contract(client, root, "lapsed", now - timedelta(days=1))
    await with_contract(client, root, "fine", now + timedelta(days=200))
    await an_org(client, root, "open-ended")
    await an_org(client, root, "frozen")
    await client.post("/api/v1/platform/organizations/frozen/suspend", headers=bearer(root))

    overview = await client.get("/api/v1/platform/overview", headers=bearer(root))
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["organizations"] >= 5
    assert body["organizations_by_status"]["suspended"] >= 1
    at_risk = {row["slug"]: row["reason"] for row in body["at_risk"]}
    assert at_risk == {"ending": "contract_ending", "lapsed": "contract_lapsed", "frozen": "suspended"}


async def test_a_renewal_records_the_dates_and_lifts_the_suspension_in_one_step(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    now = datetime.now(UTC)
    await with_contract(client, root, "kings", now - timedelta(days=1))
    await client.post("/api/v1/platform/organizations/kings/suspend", headers=bearer(root))
    org_id = (await client.get("/api/v1/orgs/kings", headers=bearer(root))).json()["id"]
    member = await make_actor(
        "member@kings.example.com",
        memberships=(Membership(org_id=uuid.UUID(org_id), org_slug="kings", role="owner"),),
        active_org_slug="kings",
    )
    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(member))).status_code == 403

    renewed = await client.post(
        "/api/v1/platform/organizations/kings/contract",
        json={"contract_ends_at": (now + timedelta(days=365)).isoformat()},
        headers=bearer(root),
    )
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["status"] == "active"
    assert renewed.json()["contract_ends_at"] is not None
    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(member))).status_code == 200

    audit = await client.get(
        "/api/v1/platform/audit?org_slug=kings&action=organization.contract_renewed", headers=bearer(root)
    )
    [row] = audit.json()["items"]
    assert row["meta"]["restored"] is True

    dates_only = await client.post(
        "/api/v1/platform/organizations/kings/contract",
        json={"contract_ends_at": (now + timedelta(days=400)).isoformat(), "restore": False},
        headers=bearer(root),
    )
    assert dates_only.json()["status"] == "active"
    assert (
        await client.post(
            "/api/v1/platform/organizations/nope/contract",
            json={"contract_ends_at": now.isoformat()},
            headers=bearer(root),
        )
    ).status_code == 404


async def test_the_console_moves_revokes_and_restores_a_membership_without_becoming_org_admin(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "kings")
    await make_actor("first@kings.example.com")
    await make_actor("second@kings.example.com")
    seated = await client.post(
        "/api/v1/platform/organizations/kings/memberships",
        json={"email": "first@kings.example.com", "role": "owner"},
        headers=bearer(root),
    )
    assert seated.status_code == 201, seated.text
    also = await client.post(
        "/api/v1/platform/organizations/kings/memberships",
        json={"email": "second@kings.example.com", "role": "supervisor"},
        headers=bearer(root),
    )
    assert also.status_code == 201, "not only the first seat"
    membership_id = also.json()["id"]

    promoted = await client.patch(
        f"/api/v1/platform/organizations/kings/memberships/{membership_id}",
        json={"role": "admin"},
        headers=bearer(root),
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "admin"

    revoked = await client.post(
        f"/api/v1/platform/organizations/kings/memberships/{membership_id}/revoke", headers=bearer(root)
    )
    assert revoked.json()["status"] == "revoked"
    restored = await client.post(
        f"/api/v1/platform/organizations/kings/memberships/{membership_id}/restore", headers=bearer(root)
    )
    assert restored.json()["status"] == "active"
    assert restored.json()["revoked_at"] is None

    # The org's own admin routes are still closed to the platform admin.
    assert (
        await client.patch(
            f"/api/v1/orgs/kings/memberships/{membership_id}", json={"role": "owner"}, headers=bearer(root)
        )
    ).status_code == 403

    actions = await client.get(
        "/api/v1/platform/audit?org_slug=kings&action=membership.", headers=bearer(root)
    )
    assert sorted(row["action"] for row in actions.json()["items"]) == [
        "membership.added",
        "membership.added",
        "membership.restored",
        "membership.revoked",
        "membership.role_changed",
    ]
    assert all(row["actor_email"] == "root@osceguide.com" for row in actions.json()["items"])
    missing = await client.post(
        f"/api/v1/platform/organizations/kings/memberships/{uuid.uuid4()}/revoke", headers=bearer(root)
    )
    assert missing.status_code == 404


async def test_org_support_is_refused_to_anybody_but_a_platform_admin(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    org = await an_org(client, root, "kings")
    admin = await make_actor(
        "admin@kings.example.com",
        memberships=(Membership(org_id=uuid.UUID(org["id"]), org_slug="kings", role="owner"),),
        active_org_slug="kings",
    )
    assert (
        await client.post(
            "/api/v1/platform/organizations/kings/contract",
            json={"contract_ends_at": datetime.now(UTC).isoformat()},
            headers=bearer(admin),
        )
    ).status_code == 403
    assert (await client.get("/api/v1/platform/overview", headers=bearer(admin))).status_code == 403


async def test_contract_dates_out_of_order_are_refused_with_a_code_and_change_nothing(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await an_org(client, root, "kings")
    url = "/api/v1/platform/organizations/kings"

    refused = await client.patch(
        url,
        json={"contract_starts_at": "2027-10-01T00:00:00Z", "contract_ends_at": "2027-01-01T00:00:00Z"},
        headers=bearer(root),
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "contract_dates_out_of_order"
    stored = (await client.get("/api/v1/orgs/kings", headers=bearer(root))).json()
    assert stored["contract_starts_at"] is None and stored["contract_ends_at"] is None

    ok = await client.patch(
        url,
        json={"contract_starts_at": "2027-01-01T00:00:00Z", "contract_ends_at": "2027-09-30T00:00:00Z"},
        headers=bearer(root),
    )
    assert ok.status_code == 200, ok.text

    # One date alone is checked against the stored other one.
    late_start = await client.patch(
        url, json={"contract_starts_at": "2028-01-01T00:00:00Z"}, headers=bearer(root)
    )
    assert late_start.status_code == 422
    assert late_start.json()["code"] == "contract_dates_out_of_order"

    # Renewing sets dates too, so the same rule applies.
    renewal = await client.post(
        f"{url}/contract",
        json={"contract_starts_at": "2028-01-01T00:00:00Z", "contract_ends_at": "2027-12-01T00:00:00Z"},
        headers=bearer(root),
    )
    assert renewal.status_code == 422
    assert renewal.json()["code"] == "contract_dates_out_of_order"
    stored = (await client.get("/api/v1/orgs/kings", headers=bearer(root))).json()
    assert stored["contract_starts_at"].startswith("2027-01-01")
    assert stored["contract_ends_at"].startswith("2027-09-30")
