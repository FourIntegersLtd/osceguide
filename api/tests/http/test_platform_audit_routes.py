"""The audit log read across every organisation, and the platform's own rows.

Those rows were written from the first day the console existed — who granted
it to whom — with no organisation, and nothing could read them back.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.http.test_platform_console_routes import an_org
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_the_platforms_own_acts_are_readable_and_filterable(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    newcomer = await make_actor("new@osceguide.com")
    found = await client.get("/api/v1/platform/users?q=new@osceguide", headers=bearer(root))
    user_id = found.json()["items"][0]["id"]
    granted = await client.put(
        f"/api/v1/platform/users/{user_id}/platform-admin",
        json={"is_platform_admin": True},
        headers=bearer(root),
    )
    assert granted.status_code == 200, granted.text
    await an_org(client, root, "kings")
    await client.patch("/api/v1/platform/organizations/kings", json={"name": "King's"}, headers=bearer(root))

    everything = await client.get("/api/v1/platform/audit", headers=bearer(root))
    assert everything.status_code == 200, everything.text
    actions = [row["action"] for row in everything.json()["items"]]
    assert "platform_admin.granted" in actions
    assert "organization.updated" in actions
    grant_row = next(row for row in everything.json()["items"] if row["action"] == "platform_admin.granted")
    assert grant_row["org_id"] is None
    assert grant_row["actor_email"] == "root@osceguide.com"
    assert grant_row["target_id"] == user_id

    only_kings = await client.get("/api/v1/platform/audit?org_slug=kings", headers=bearer(root))
    assert {row["action"] for row in only_kings.json()["items"]} == {
        "organization.provisioned",
        "organization.updated",
    }
    assert all(row["org_id"] for row in only_kings.json()["items"])
    only_grants = await client.get("/api/v1/platform/audit?action=platform_admin.", headers=bearer(root))
    assert {row["action"] for row in only_grants.json()["items"]} == {"platform_admin.granted"}
    nobody = await client.get("/api/v1/platform/audit?actor_email=new@osceguide.com", headers=bearer(root))
    assert nobody.json()["items"] == []
    _ = newcomer

    unknown_org = await client.get("/api/v1/platform/audit?org_slug=nope", headers=bearer(root))
    assert unknown_org.status_code == 404


async def test_a_persons_history_is_what_was_done_to_them_and_what_they_did(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await make_actor("subject@example.com")
    found = await client.get("/api/v1/platform/users?q=subject@", headers=bearer(root))
    user_id = found.json()["items"][0]["id"]
    await client.patch(f"/api/v1/platform/users/{user_id}", json={"name": "Renamed"}, headers=bearer(root))
    await client.put(
        f"/api/v1/platform/users/{user_id}/platform-admin",
        json={"is_platform_admin": True},
        headers=bearer(root),
    )

    history = await client.get(f"/api/v1/platform/users/{user_id}/audit", headers=bearer(root))
    assert history.status_code == 200, history.text
    assert [row["action"] for row in history.json()["items"]] == ["platform_admin.granted", "user.updated"]

    root_history = await client.get(
        "/api/v1/platform/audit?actor_email=root@osceguide.com", headers=bearer(root)
    )
    assert len(root_history.json()["items"]) >= 2
    missing = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/audit", headers=bearer(root))
    assert missing.status_code == 404


async def test_only_a_platform_admin_reads_the_audit_log(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("someone@example.com")
    assert (await client.get("/api/v1/platform/audit", headers=bearer(someone))).status_code == 403
