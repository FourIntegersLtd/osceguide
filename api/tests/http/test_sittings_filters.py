"""R-31: the sittings list filters on the server, so a filter sees every page, not the loaded ones."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sittings.models import Sitting
from tests.http.test_results_routes import org_with_admin
from tests.support.rubrics import published_feedback_version
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def three_sittings(db_session: AsyncSession, org_id: uuid.UUID) -> None:
    version = await published_feedback_version(db_session, org_id)
    await db_session.flush()
    for name, status, day in (
        ("March", "completed", datetime(2026, 3, 10, tzinfo=UTC)),
        ("May", "scheduled", datetime(2026, 5, 10, tzinfo=UTC)),
        ("June", "scheduled", datetime(2026, 6, 10, tzinfo=UTC)),
    ):
        db_session.add(
            Sitting(
                org_id=org_id,
                name=name,
                mode="exam",
                status=status,
                scheduled_for=day,
                rubric_version_id=version.id,
            )
        )
    await db_session.flush()


async def names(client: AsyncClient, admin: str, query: str) -> list[str]:
    response = await client.get(f"/api/v1/orgs/kings/sittings?{query}", headers=bearer(admin))
    assert response.status_code == 200, response.text
    return sorted(item["name"] for item in response.json()["items"])


async def test_the_list_filters_by_status_and_date_across_pages(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await three_sittings(db_session, org_id)

    assert await names(client, admin, "status=completed") == ["March"]
    assert await names(client, admin, "scheduled_from=2026-05-01&scheduled_to=2026-05-31") == ["May"]
    assert await names(client, admin, "status=scheduled&scheduled_from=2026-05-11") == ["June"]
    # A filter narrows the pages, it does not stop paging: one row per page, still all found.
    first = await client.get("/api/v1/orgs/kings/sittings?status=scheduled&limit=1", headers=bearer(admin))
    second = await client.get(
        f"/api/v1/orgs/kings/sittings?status=scheduled&limit=1&cursor={first.json()['next_cursor']}",
        headers=bearer(admin),
    )
    assert sorted(item["name"] for item in first.json()["items"] + second.json()["items"]) == ["June", "May"]
    assert first.json()["next_cursor"] is not None
    assert await names(client, admin, f"programme_id={uuid.uuid4()}") == []
    assert await names(client, admin, "status=nonsense") == []


async def test_the_list_filters_by_mode_and_name_search_across_pages(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await three_sittings(db_session, org_id)
    version = await published_feedback_version(db_session, org_id)
    db_session.add(
        Sitting(org_id=org_id, name="Mayfair drill", mode="training", rubric_version_id=version.id)
    )
    await db_session.flush()

    assert await names(client, admin, "mode=training") == ["Mayfair drill"]
    assert await names(client, admin, "mode=exam") == ["June", "March", "May"]
    assert await names(client, admin, "search=may") == ["May", "Mayfair drill"]
    assert await names(client, admin, "search=may&mode=exam") == ["May"]
    # A percent sign is text, not a wildcard.
    assert await names(client, admin, "search=%25") == []
    first = await client.get("/api/v1/orgs/kings/sittings?search=may&limit=1", headers=bearer(admin))
    second = await client.get(
        f"/api/v1/orgs/kings/sittings?search=may&limit=1&cursor={first.json()['next_cursor']}",
        headers=bearer(admin),
    )
    assert sorted(item["name"] for item in first.json()["items"] + second.json()["items"]) == [
        "May",
        "Mayfair drill",
    ]


async def test_a_mode_that_is_not_a_mode_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)

    refused = await client.get("/api/v1/orgs/kings/sittings?mode=nonsense", headers=bearer(admin))

    assert refused.status_code == 422
