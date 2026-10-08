"""Who may read each dashboard route, and what each says when there is nothing to show.

Every route of the dashboard slice, called as each kind of caller. The behaviour
behind the routes lives in the sibling files (`test_org_read_models`, `test_live_board`,
`test_sitting_report` ...); this file is the role matrix and the error codes.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.roles import assert_unauthenticated, callers, refused
from tests.support.sittings import a_sitting, org_by_slug
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

ORG = "/api/v1/orgs/kings"
NOBODY = uuid.UUID(int=1)

# (path, status an allowed caller gets for an id that does not exist, its code)
STAFF_READS = [
    (f"{ORG}/dashboard", 200, None),
    (f"{ORG}/reporting", 200, None),
    (f"{ORG}/supervisor/circuits", 200, None),
    (f"{ORG}/live", 200, None),
    (f"{ORG}/live/history", 200, None),
    (f"{ORG}/circuits/{NOBODY}/console", 404, "circuit_not_found"),
    (f"{ORG}/sittings/{NOBODY}/report", 404, "sitting_not_found"),
    (f"{ORG}/sittings/{NOBODY}/cohort", 404, "sitting_not_found"),
]
ADMIN_READS = [
    (f"{ORG}/sittings/{NOBODY}/report.csv", 404, "sitting_not_found"),
    (f"{ORG}/sittings/{NOBODY}/readout", 404, "sitting_not_found"),
]


async def test_a_stranger_and_a_candidate_are_refused_every_org_read(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for role in ("stranger", "trainee"):
        for path, _, _ in STAFF_READS + ADMIN_READS:
            await refused(client, who[role], "GET", path)


async def test_staff_read_what_staff_run_and_get_the_literal_not_found_for_a_missing_id(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for role in ("supervisor", "partner_admin", "owner", "platform"):
        for path, status, code in STAFF_READS:
            response = await client.get(path, headers=who[role])
            assert response.status_code == status, (role, path, response.text)
            if code:
                assert response.json()["code"] == code, (role, path)


async def test_only_an_institution_admin_gets_past_the_export_routes(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for path, status, code in ADMIN_READS:
        for role in ("supervisor", "platform"):
            await refused(client, who[role], "GET", path)
        for role in ("owner", "partner_admin"):  # a partner admin is an org admin, not an institution admin
            response = await client.get(path, headers=who[role])
            assert (response.status_code, response.json()["code"]) == (status, code), (role, path)


async def test_an_organisation_with_nothing_in_it_reads_as_empty_not_as_an_error(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    owner = (await callers(client, make_actor))["owner"]
    live = (await client.get(f"{ORG}/live", headers=owner)).json()
    assert live["circuits"] == []
    mine = (await client.get(f"{ORG}/supervisor/circuits", headers=owner)).json()
    assert mine == {"items": []}


async def test_an_unknown_organisation_is_refused_to_everyone_but_the_platform(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    response = await client.get("/api/v1/orgs/nowhere/dashboard", headers=who["owner"])
    assert (response.status_code, response.json()["code"]) == (403, "forbidden")


async def test_the_live_history_pages_newest_first_and_the_cursor_ends(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime, timedelta

    from app.features.sittings.models import CircuitRunHistory

    who = await callers(client, make_actor)
    org_id = (await org_by_slug(db_session, "kings")).id
    start = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
    for i in range(3):
        db_session.add(
            CircuitRunHistory(
                org_id=org_id,
                circuit_name=f"Circuit {i}",
                sitting_name="Finals",
                mode="exam",
                started_at=start,
                ended_at=start + timedelta(hours=i + 1),
                candidate_count=4,
                stations_total=2,
                stations_completed=2,
                status="completed",
            )
        )
    await db_session.flush()
    url = f"{ORG}/live/history"
    first = (await client.get(f"{url}?limit=2", headers=who["supervisor"])).json()
    assert [r["circuit_name"] for r in first["items"]] == ["Circuit 2", "Circuit 1"]
    assert first["next_cursor"] is not None
    second = (
        await client.get(f"{url}?limit=2&cursor={first['next_cursor']}", headers=who["supervisor"])
    ).json()
    assert [r["circuit_name"] for r in second["items"]] == ["Circuit 0"]
    assert second["next_cursor"] is None
    assert (await client.get(f"{url}?limit=0", headers=who["owner"])).status_code == 422
    garbage = await client.get(f"{url}?cursor=not-a-cursor", headers=who["owner"])
    assert garbage.status_code == 422, garbage.text


async def test_the_trainee_routes_need_a_token_and_start_empty(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    for path in (
        "/api/v1/me/dashboard",
        "/api/v1/me/performance",
        "/api/v1/me/sittings",
        "/api/v1/me/achievements",
    ):
        await assert_unauthenticated(client, "GET", path)
    token = bearer(await make_actor("nobody@example.com"))
    assert (await client.get("/api/v1/me/sittings", headers=token)).json() == {"items": []}
    unknown = await client.get("/api/v1/me/performance?exam_code=nope", headers=token)
    assert unknown.status_code == 404, unknown.text


async def test_the_platform_directory_is_for_platform_admins_and_a_missing_user_is_a_404(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for path in (
        "/api/v1/platform/directory",
        "/api/v1/platform/directory/summary",
        f"/api/v1/platform/directory/users/{NOBODY}",
    ):
        await refused(client, who["owner"], "GET", path)
    missing = await client.get(f"/api/v1/platform/directory/users/{NOBODY}", headers=who["platform"])
    assert (missing.status_code, missing.json()["code"]) == (404, "user_not_found")


async def test_the_streams_refuse_the_same_callers_the_reads_do(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for path in (f"{ORG}/live/stream", f"{ORG}/circuits/{NOBODY}/console/stream"):
        await refused(client, who["trainee"], "GET", path)
    await assert_unauthenticated(client, "GET", "/api/v1/me/sittings/stream")


async def test_another_organisations_sitting_is_not_found_in_every_sitting_read(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor, "kings")
    other = await callers(client, make_actor, "guys")
    sitting = await a_sitting(client, who.tokens["owner"], "kings")
    for tail in ("report", "report.csv", "cohort", "readout"):
        response = await client.get(
            f"/api/v1/orgs/guys/sittings/{sitting['id']}/{tail}", headers=other["owner"]
        )
        assert (response.status_code, response.json()["code"]) == (404, "sitting_not_found"), tail
