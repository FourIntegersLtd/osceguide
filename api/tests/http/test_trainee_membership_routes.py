"""Rostering a trainee makes them a member, and staff data is closed to trainees (D11, B4)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.identity import repository as identity_repository
from app.features.tenancy.models import Membership as MembershipRow
from tests.http.test_roster_routes import add_trainee, org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def roles_of(db_session: AsyncSession, email: str) -> list[tuple[str, str]]:
    user = await identity_repository.user_by_email(db_session, email)
    assert user is not None
    rows = await db_session.execute(
        select(MembershipRow.role, MembershipRow.status).where(MembershipRow.user_id == user.id)
    )
    return sorted((role, status) for role, status in rows.all())


async def test_rostering_grants_a_trainee_membership_and_revoke_restore_toggle_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee_id = await add_trainee(client, admin, "alice@example.com")
    assert await roles_of(db_session, "alice@example.com") == [("trainee", "active")]

    revoked = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access", json={"revoked": True}, headers=bearer(admin)
    )
    assert revoked.status_code == 200, revoked.text
    assert await roles_of(db_session, "alice@example.com") == [("trainee", "revoked")]

    await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access", json={"revoked": False}, headers=bearer(admin)
    )
    assert await roles_of(db_session, "alice@example.com") == [("trainee", "active")]


async def test_delete_and_anonymise_revoke_the_membership(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    gone = await add_trainee(client, admin, "gone@example.com")
    scrubbed = await add_trainee(client, admin, "scrub@example.com")
    assert (
        await client.delete(f"/api/v1/orgs/kings/trainees/{gone}", headers=bearer(admin))
    ).status_code == 204
    assert (
        await client.post(f"/api/v1/orgs/kings/trainees/{scrubbed}/anonymise", headers=bearer(admin))
    ).status_code == 200
    assert await roles_of(db_session, "gone@example.com") == [("trainee", "revoked")]
    assert await roles_of(db_session, "scrub@example.com") == [("trainee", "revoked")]


async def test_a_rostered_supervisor_keeps_one_membership_and_the_team_list_hides_trainees(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await make_actor(
        "sue@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    await add_trainee(client, admin, "sue@example.com")
    await add_trainee(client, admin, "bob@example.com")
    assert await roles_of(db_session, "sue@example.com") == [("supervisor", "active")]
    assert await roles_of(db_session, "bob@example.com") == [("trainee", "active")]

    team = await client.get("/api/v1/orgs/kings/memberships", headers=bearer(admin))
    roles = sorted(item["role"] for item in team.json()["items"])
    assert roles == ["owner", "supervisor"]


STAFF_READS = [
    "/api/v1/orgs/kings/trainees",
    "/api/v1/orgs/kings/cohorts",
    "/api/v1/orgs/kings/trainee-groups",
    "/api/v1/orgs/kings/sittings",
    "/api/v1/orgs/kings/exams",
    "/api/v1/orgs/kings/programmes",
    "/api/v1/orgs/kings/rubrics",
    "/api/v1/orgs/kings/station-templates",
    "/api/v1/orgs/kings/dashboard",
    "/api/v1/orgs/kings/supervisor/circuits",
]


@pytest.mark.parametrize("path", STAFF_READS)
async def test_staff_reads_are_closed_to_trainees_and_open_to_supervisors(
    client: AsyncClient, make_actor, path: str
) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await org_with_admin(client, make_actor)
    trainee = await make_actor(
        "t@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    supervisor = await make_actor(
        "s@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    assert (await client.get(path, headers=bearer(trainee))).status_code == 403
    assert (await client.get(path, headers=bearer(supervisor))).status_code == 200


async def test_review_and_console_reads_are_closed_to_trainees(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await org_with_admin(client, make_actor)
    trainee = await make_actor(
        "t2@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    any_id = uuid.uuid4()
    for path in (
        f"/api/v1/orgs/kings/slots/{any_id}/reviews",
        f"/api/v1/orgs/kings/circuits/{any_id}/review",
        f"/api/v1/orgs/kings/circuits/{any_id}/console",
        f"/api/v1/orgs/kings/sittings/{any_id}",
        f"/api/v1/orgs/kings/sittings/{any_id}/cohort",
        f"/api/v1/orgs/kings/rubrics/{any_id}",
    ):
        assert (await client.get(path, headers=bearer(trainee))).status_code == 403, path
