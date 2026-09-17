"""Contract dates were recorded and enforced by nothing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.tenancy import domain
from app.features.tenancy.service_platform import suspend_lapsed_organizations
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)


def test_no_end_date_is_open_ended() -> None:
    assert domain.contract_lapsed(None, now=NOW) is False


def test_a_contract_ends_at_its_end() -> None:
    assert domain.contract_lapsed(NOW, now=NOW) is True
    assert domain.contract_lapsed(NOW + timedelta(seconds=1), now=NOW) is False


async def provisioned(client: AsyncClient, root: str, slug: str, ends_at: datetime | None) -> None:
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    if ends_at is not None:
        patched = await client.patch(
            f"/api/v1/platform/organizations/{slug}",
            json={"contract_ends_at": ends_at.isoformat()},
            headers=bearer(root),
        )
        assert patched.status_code == 200, patched.text


async def test_only_lapsed_contracts_are_suspended(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await provisioned(client, root, "lapsed", NOW - timedelta(days=1))
    await provisioned(client, root, "current", NOW + timedelta(days=30))
    await provisioned(client, root, "open-ended", None)

    assert await suspend_lapsed_organizations(db_session, now=NOW) == ["lapsed"]

    statuses = {
        o["slug"]: o["status"]
        for o in (await client.get("/api/v1/platform/organizations", headers=bearer(root))).json()["items"]
    }
    assert statuses["lapsed"] == "suspended"
    assert statuses["current"] == "trial"
    assert statuses["open-ended"] == "trial"

    # Running again does nothing: a suspended organisation is not re-suspended.
    assert await suspend_lapsed_organizations(db_session, now=NOW) == []


async def test_renewing_is_a_new_end_date_and_a_restore(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await provisioned(client, root, "renewing", NOW - timedelta(days=1))
    await suspend_lapsed_organizations(db_session, now=NOW)

    await client.patch(
        "/api/v1/platform/organizations/renewing",
        json={"contract_ends_at": (NOW + timedelta(days=365)).isoformat()},
        headers=bearer(root),
    )
    restored = await client.post("/api/v1/platform/organizations/renewing/restore", headers=bearer(root))
    assert restored.json()["status"] == "active"
    assert await suspend_lapsed_organizations(db_session, now=NOW) == []
