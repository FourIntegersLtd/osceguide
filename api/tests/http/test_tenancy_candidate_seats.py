"""An employer's plan seats: platform staff set them, the organisation's admin reads them (hire Settings)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_staff_set_seats_and_the_admin_reads_them_but_cannot_change_them(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    root = await make_actor("root2@osceguide.com", platform_admin=True)

    before = await client.get("/api/v1/orgs/kings", headers=bearer(admin))
    assert before.json()["candidate_seats"] is None

    staff = await client.patch(
        "/api/v1/platform/organizations/kings", json={"candidate_seats": 120}, headers=bearer(root)
    )
    assert (staff.status_code, staff.json()["candidate_seats"]) == (200, 120)

    own = await client.patch(
        "/api/v1/orgs/kings", json={"name": "Kings Trust", "candidate_seats": 9999}, headers=bearer(admin)
    )
    assert (own.status_code, own.json()["candidate_seats"], own.json()["name"]) == (200, 120, "Kings Trust")

    refused = await client.patch(
        "/api/v1/platform/organizations/kings", json={"candidate_seats": -1}, headers=bearer(root)
    )
    assert refused.status_code == 422
