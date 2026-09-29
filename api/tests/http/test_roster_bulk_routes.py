"""Bulk roster actions the retiring b2b client offered and the platform did
not: revoking a selection, moving a selection to a different intake, and
resending a selection's invitations, all in one request.

Each route is a thin wrapper around the single-row route it matches
(`POST /trainees/{id}/access`, `PATCH /trainees/{id}`,
`POST /trainees/{id}/resend-invitation`); these tests prove the batch
reports the right outcome per row rather than re-testing those routes' own
business rules again.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.notifications.models import OutboundMessage
from tests.http.test_roster_routes import add_trainee, org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

KINGS = "/api/v1/orgs/kings"


async def a_cohort(client: AsyncClient, admin: str, name: str, slug: str = "kings") -> str:
    response = await client.post(f"/api/v1/orgs/{slug}/cohorts", json={"name": name}, headers=bearer(admin))
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


# --------------------------------------------------------------------------
# POST /trainees/bulk/revoke
# --------------------------------------------------------------------------


async def test_a_selection_is_revoked_in_one_request(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    first = await add_trainee(client, admin, "first@example.com")
    second = await add_trainee(client, admin, "second@example.com")

    response = await client.post(
        f"{KINGS}/trainees/bulk/revoke", json={"trainee_ids": [first, second]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [
        {"trainee_id": first, "outcome": "revoked"},
        {"trainee_id": second, "outcome": "revoked"},
    ]

    listed = (await client.get(f"{KINGS}/trainees", headers=bearer(admin))).json()
    assert {t["id"]: t["access_revoked"] for t in listed["items"]} == {first: True, second: True}


async def test_an_already_revoked_row_is_reported_not_re_revoked(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "twice@example.com")
    await client.post(f"{KINGS}/trainees/{trainee}/access", json={"revoked": True}, headers=bearer(admin))

    response = await client.post(
        f"{KINGS}/trainees/bulk/revoke", json={"trainee_ids": [trainee]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": trainee, "outcome": "already_revoked"}]


async def test_an_unknown_id_in_a_revoke_batch_is_not_found_not_fatal(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    real = await add_trainee(client, admin, "real@example.com")
    missing = str(uuid.uuid4())

    response = await client.post(
        f"{KINGS}/trainees/bulk/revoke", json={"trainee_ids": [real, missing]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [
        {"trainee_id": real, "outcome": "revoked"},
        {"trainee_id": missing, "outcome": "not_found"},
    ]


async def test_a_repeated_id_is_processed_once(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "repeated@example.com")

    response = await client.post(
        f"{KINGS}/trainees/bulk/revoke",
        json={"trainee_ids": [trainee, trainee]},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": trainee, "outcome": "revoked"}]


async def test_an_admin_of_one_org_cannot_bulk_revoke_anothers_trainee(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Tenant isolation: an id from another organisation is `not_found`, never touched."""
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    theirs = await add_trainee(client, guys_admin, "theirs@example.com", slug="guys")

    response = await client.post(
        f"{KINGS}/trainees/bulk/revoke", json={"trainee_ids": [theirs]}, headers=bearer(kings_admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": theirs, "outcome": "not_found"}]

    # The other organisation's trainee is genuinely untouched.
    still_theirs = (await client.get("/api/v1/orgs/guys/trainees", headers=bearer(guys_admin))).json()
    assert still_theirs["items"][0]["access_revoked"] is False


async def test_a_supervisor_cannot_bulk_revoke(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "supervised@example.com")
    supervisor = await make_actor(
        "supervisor-kings@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    refused = await client.post(
        f"{KINGS}/trainees/bulk/revoke", json={"trainee_ids": [trainee]}, headers=bearer(supervisor)
    )
    assert refused.status_code == 403, refused.text


async def test_an_empty_selection_is_invalid(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    response = await client.post(
        f"{KINGS}/trainees/bulk/revoke", json={"trainee_ids": []}, headers=bearer(admin)
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# POST /trainees/bulk/cohort
# --------------------------------------------------------------------------


async def test_a_selection_is_moved_to_one_intake(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "September 2026")
    first = await add_trainee(client, admin, "moved1@example.com")
    second = await add_trainee(client, admin, "moved2@example.com")

    response = await client.post(
        f"{KINGS}/trainees/bulk/cohort",
        json={"trainee_ids": [first, second], "cohort_id": cohort},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [
        {"trainee_id": first, "outcome": "updated"},
        {"trainee_id": second, "outcome": "updated"},
    ]

    listed = (await client.get(f"{KINGS}/trainees", headers=bearer(admin))).json()
    assert {t["id"]: t["cohort_id"] for t in listed["items"]} == {first: cohort, second: cohort}


async def test_a_null_cohort_clears_the_intake_for_a_selection(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "June 2027")
    trainee = await add_trainee(client, admin, "leaver@example.com")
    await client.patch(f"{KINGS}/trainees/{trainee}", json={"cohort_id": cohort}, headers=bearer(admin))

    response = await client.post(
        f"{KINGS}/trainees/bulk/cohort",
        json={"trainee_ids": [trainee], "cohort_id": None},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": trainee, "outcome": "updated"}]
    listed = (await client.get(f"{KINGS}/trainees", headers=bearer(admin))).json()
    assert listed["items"][0]["cohort_id"] is None


async def test_a_cohort_from_another_org_refuses_the_whole_batch(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    outsider = await a_cohort(client, guys_admin, "Guy's intake", slug="guys")
    trainee = await add_trainee(client, kings_admin, "attached@example.com")

    refused = await client.post(
        f"{KINGS}/trainees/bulk/cohort",
        json={"trainee_ids": [trainee], "cohort_id": outsider},
        headers=bearer(kings_admin),
    )
    assert refused.status_code == 404, refused.text
    assert refused.json()["code"] == "cohort_not_found"


async def test_an_unknown_id_in_a_cohort_batch_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "March 2027")
    real = await add_trainee(client, admin, "real2@example.com")
    missing = str(uuid.uuid4())

    response = await client.post(
        f"{KINGS}/trainees/bulk/cohort",
        json={"trainee_ids": [real, missing], "cohort_id": cohort},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [
        {"trainee_id": real, "outcome": "updated"},
        {"trainee_id": missing, "outcome": "not_found"},
    ]


# --------------------------------------------------------------------------
# POST /trainees/bulk/resend-invitation
# --------------------------------------------------------------------------


async def invitations_to(db_session: AsyncSession, recipient: str) -> list[OutboundMessage]:
    stmt = (
        select(OutboundMessage)
        .where(OutboundMessage.template_key == "invitation", OutboundMessage.recipient == recipient)
        .order_by(OutboundMessage.available_at)
    )
    return list((await db_session.execute(stmt)).scalars())


async def test_a_selection_is_reinvited_in_one_request(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "lost@example.com")

    response = await client.post(
        f"{KINGS}/trainees/bulk/resend-invitation", json={"trainee_ids": [trainee]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": trainee, "outcome": "sent"}]
    assert len(await invitations_to(db_session, "lost@example.com")) == 2


async def test_someone_who_already_signed_in_is_reported_not_resent(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "joined@example.com")
    queued = await invitations_to(db_session, "joined@example.com")
    await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": queued[0].payload["token"], "password": "Str0ng-Passw0rd!"},  # type: ignore[attr-defined]
    )

    response = await client.post(
        f"{KINGS}/trainees/bulk/resend-invitation", json={"trainee_ids": [trainee]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": trainee, "outcome": "already_signed_in"}]
    assert len(await invitations_to(db_session, "joined@example.com")) == 1


async def test_an_unknown_id_in_a_resend_batch_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    missing = str(uuid.uuid4())

    response = await client.post(
        f"{KINGS}/trainees/bulk/resend-invitation", json={"trainee_ids": [missing]}, headers=bearer(admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["results"] == [{"trainee_id": missing, "outcome": "not_found"}]
