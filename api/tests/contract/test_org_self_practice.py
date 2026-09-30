"""An institution's trainee practising on their own.

b2b served this with eleven routes under `/practice/{org}` — its own exam
list, its own station list, its own mock creation, its own history — because
its practice users were a separate kind of account from its candidates.

Here it is the same attempt every other consumer makes, with an org on it, so
there is nothing to build: this test exists to prove that, because the
alternative was porting eleven routes that would have duplicated `attempts`,
`stations` and `dashboard` for one audience.

If this ever fails, the parity gap is real and the routes have to be written
after all.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_an_org_trainee_practises_alone_with_no_routes_of_their_own(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    version_id = await published_station(client, admin, "kings", "Chest pain")

    trainee = await make_actor(
        "selfpractice@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    # Access comes from the institution, not from a card. `org_grant` is the
    # entitlement source that replaces b2b's `b2b_practice_entitlements`.
    granted = await client.post(
        "/api/v1/orgs/kings/entitlements",
        json={"email": "selfpractice@example.com", "exam_code": "sca"},
        headers=bearer(admin),
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["source"] == "org_grant"

    # They can see what their institution wrote, because being a member is
    # the permission — no separate practice-station list.
    stations = await client.get("/api/v1/orgs/kings/stations", headers=bearer(trainee))
    assert stations.status_code == 200
    assert [s["title"] for s in stations.json()["items"]] == ["Chest pain"]

    started = await client.post(
        "/api/v1/attempts",
        json={"kind": "self_practice", "exam_code": "sca", "station_version_id": str(version_id)},
        headers=bearer(trainee),
    )
    assert started.status_code == 201, started.text
    assert started.json()["kind"] == "self_practice"

    # And their history is the ordinary one. b2b had `/practice/{org}/history`.
    dashboard = await client.get("/api/v1/me/dashboard", headers=bearer(trainee))
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert [e["source"] for e in body["entitlements"]] == ["org_grant"]
    assert body["progress"][0]["attempts"] == 1
    assert body["recent_attempts"][0]["id"] == started.json()["id"]


async def test_a_trainee_cannot_practise_without_the_institution_granting_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Membership is not access.

    Being rostered onto an institution says who you are, not what you have
    been bought. b2b kept those in one table and an admin adding somebody to
    the org gave them the practice product by accident.
    """
    from sqlalchemy import update

    from app.features.identity.models import User

    org_id, admin = await org_with_admin(client, make_actor, slug="guys")
    version_id = await published_station(client, admin, "guys", "Breathlessness")
    trainee = await make_actor(
        "ungranted@example.com",
        memberships=(Membership(org_id=org_id, org_slug="guys", role="trainee"),),
        active_org_slug="guys",
    )
    # Aged past the free trial, which would otherwise let them start anyway
    # and prove nothing about the grant.
    from datetime import UTC, datetime, timedelta

    await db_session.execute(
        update(User)
        .where(User.email == "ungranted@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()

    refused = await client.post(
        "/api/v1/attempts",
        json={"kind": "self_practice", "exam_code": "sca", "station_version_id": str(version_id)},
        headers=bearer(trainee),
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "not_entitled"
