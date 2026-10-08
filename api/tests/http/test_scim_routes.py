"""SCIM 2.0 provisioning of a roster by an identity provider (E-21).

Driven with the request shapes Entra's provisioning service sends: find by
`userName eq`, create, `Replace active "False"`, group member add and remove.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.notifications.models import OutboundMessage
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

SCIM = "/api/v1/orgs/kings/scim/v2"
USER = "urn:ietf:params:scim:schemas:core:2.0:User"


async def an_org_with_a_connector(client: AsyncClient, make_actor, slug: str = "kings") -> tuple[str, str]:  # type: ignore[no-untyped-def]
    """An organisation, its admin, and a SCIM token that admin issued."""
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
    issued = await client.post(
        f"/api/v1/orgs/{slug}/scim/tokens", json={"label": "Entra"}, headers=bearer(admin)
    )
    assert issued.status_code == 201, issued.text
    return admin, issued.json()["token"]


def scim_user(email: str, **extra: object) -> dict[str, object]:
    return {
        "schemas": [USER],
        "userName": email,
        "name": {"givenName": "Ana", "familyName": "Lee"},
        "emails": [{"value": email, "primary": True, "type": "work"}],
        "active": True,
        "externalId": "entra-object-id",
        "title": "Registrar",
        **extra,
    }


async def test_a_user_is_found_created_deactivated_and_kept(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    admin, token = await an_org_with_a_connector(client, make_actor)
    headers = bearer(token)

    missing = await client.get(
        f"{SCIM}/Users", params={"filter": 'userName eq "ana@nhs.net"'}, headers=headers
    )
    assert missing.status_code == 200, missing.text
    assert missing.headers["content-type"].startswith("application/scim+json")
    assert missing.json()["totalResults"] == 0 and missing.json()["Resources"] == []

    created = await client.post(
        f"{SCIM}/Users",
        json=scim_user("ana@nhs.net"),
        headers={**headers, "content-type": "application/scim+json"},
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["userName"] == "ana@nhs.net"
    assert user["name"] == {"givenName": "Ana", "familyName": "Lee"}
    assert user["active"] is True
    assert user["meta"]["resourceType"] == "User"
    assert user["meta"]["location"].endswith(f"/scim/v2/Users/{user['id']}")

    # The same use case the roster screen runs: an invitation went out.
    invited = (
        await db_session.execute(
            select(OutboundMessage.recipient).where(OutboundMessage.template_key == "invitation")
        )
    ).scalars()
    assert "ana@nhs.net" in set(invited)
    roster = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()["items"]
    assert [trainee["id"] for trainee in roster] == [user["id"]]

    found = await client.get(f"{SCIM}/Users", params={"filter": 'userName eq "ANA@nhs.net"'}, headers=headers)
    assert [resource["id"] for resource in found.json()["Resources"]] == [user["id"]]

    duplicate = await client.post(f"{SCIM}/Users", json=scim_user("ana@nhs.net"), headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["scimType"] == "uniqueness"
    assert duplicate.json()["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:Error"]

    patched = await client.patch(
        f"{SCIM}/Users/{user['id']}",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [
                {"op": "Replace", "path": "active", "value": "False"},
                {"op": "Replace", "path": "name.givenName", "value": "Anna"},
            ],
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert (patched.json()["active"], patched.json()["name"]["givenName"]) == (False, "Anna")
    revoked = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()["items"][0]
    assert revoked["access_revoked"] is True

    replaced = await client.put(
        f"{SCIM}/Users/{user['id']}", json=scim_user("ana@nhs.net", active=True), headers=headers
    )
    assert replaced.json()["active"] is True and replaced.json()["name"]["givenName"] == "Ana"

    renamed_address = await client.put(
        f"{SCIM}/Users/{user['id']}", json=scim_user("new@nhs.net"), headers=headers
    )
    assert renamed_address.status_code == 400
    assert renamed_address.json()["scimType"] == "mutability"

    deleted = await client.delete(f"{SCIM}/Users/{user['id']}", headers=headers)
    assert deleted.status_code == 204
    kept = await client.get(f"{SCIM}/Users/{user['id']}", headers=headers)
    assert kept.status_code == 200 and kept.json()["active"] is False, (
        "deleting deactivates; the record stays"
    )


async def test_a_group_is_provisioned_onto_the_roster_groups(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, token = await an_org_with_a_connector(client, make_actor)
    headers = bearer(token)
    first = (await client.post(f"{SCIM}/Users", json=scim_user("one@nhs.net"), headers=headers)).json()["id"]
    second = (await client.post(f"{SCIM}/Users", json=scim_user("two@nhs.net"), headers=headers)).json()["id"]

    created = await client.post(
        f"{SCIM}/Groups",
        json={"displayName": "FY1 Cohort", "members": [{"value": first}]},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    group = created.json()
    assert [member["value"] for member in group["members"]] == [first]

    patched = await client.patch(
        f"{SCIM}/Groups/{group['id']}",
        json={
            "Operations": [
                {"op": "Add", "path": "members", "value": [{"value": second}]},
                {"op": "Remove", "path": f'members[value eq "{first}"]'},
                {"op": "Replace", "path": "displayName", "value": "FY1 Thursday"},
            ]
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["displayName"] == "FY1 Thursday"
    assert [member["value"] for member in patched.json()["members"]] == [second]

    listed = (await client.get("/api/v1/orgs/kings/trainee-groups", headers=bearer(admin))).json()["items"]
    assert [(row["label"], row["member_count"]) for row in listed] == [("FY1 Thursday", 1)]
    found = await client.get(
        f"{SCIM}/Groups", params={"filter": 'displayName eq "fy1 thursday"'}, headers=headers
    )
    assert found.json()["totalResults"] == 1

    stranger = await client.patch(
        f"{SCIM}/Groups/{group['id']}",
        json={"Operations": [{"op": "Add", "path": "members", "value": [{"value": str(uuid.uuid4())}]}]},
        headers=headers,
    )
    assert stranger.status_code == 400
    assert stranger.json()["scimType"] == "invalidValue"

    deleted = await client.delete(f"{SCIM}/Groups/{group['id']}", headers=headers)
    assert deleted.status_code == 204, "a connector's delete empties and removes the group"
    assert (await client.get(f"{SCIM}/Groups/{group['id']}", headers=headers)).status_code == 404


async def test_only_this_organisations_live_token_is_let_in(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, token = await an_org_with_a_connector(client, make_actor, "kings")
    _, guys_token = await an_org_with_a_connector(client, make_actor, "guys")

    for headers in ({}, {"Authorization": "Basic abc"}, bearer("scim_not-a-token"), bearer(guys_token)):
        refused = await client.get(f"{SCIM}/Users", headers=headers)
        assert refused.status_code == 401, headers
        assert refused.json()["code"] == "scim_unauthorized"

    tokens = (await client.get("/api/v1/orgs/kings/scim/tokens", headers=bearer(admin))).json()
    assert len(tokens) == 1 and "token" not in tokens[0]
    assert token.startswith(tokens[0]["token_prefix"])
    assert (await client.get(f"{SCIM}/Users", headers=bearer(token))).status_code == 200
    used = (await client.get("/api/v1/orgs/kings/scim/tokens", headers=bearer(admin))).json()[0]
    assert used["last_used_at"] is not None

    revoked = await client.delete(f"/api/v1/orgs/kings/scim/tokens/{tokens[0]['id']}", headers=bearer(admin))
    assert revoked.status_code == 204
    assert (await client.get(f"{SCIM}/Users", headers=bearer(token))).status_code == 401


async def test_an_unsupported_filter_is_refused_in_scims_terms(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, token = await an_org_with_a_connector(client, make_actor)
    refused = await client.get(
        f"{SCIM}/Users", params={"filter": 'title eq "Registrar"'}, headers=bearer(token)
    )
    assert refused.status_code == 400
    assert refused.json()["scimType"] == "invalidFilter"


async def test_the_server_says_what_it_supports(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, token = await an_org_with_a_connector(client, make_actor)
    config = await client.get(f"{SCIM}/ServiceProviderConfig", headers=bearer(token))
    assert config.status_code == 200, config.text
    assert config.json()["patch"] == {"supported": True}
    assert config.json()["bulk"]["supported"] is False


async def test_a_trainee_cannot_issue_a_scim_token(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, _ = await an_org_with_a_connector(client, make_actor)
    stranger = await make_actor("not-an-admin@example.com")
    refused = await client.post(
        "/api/v1/orgs/kings/scim/tokens", json={"label": "x"}, headers=bearer(stranger)
    )
    assert refused.status_code == 403


async def test_a_deprovisioned_user_is_absent_from_unstarted_stations(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-18: the directory dropped them, but their stations in circuits still to run stayed scheduled."""
    from app.features.sittings.models import Slot
    from tests.http.test_org_read_models import a_circuit
    from tests.http.test_sittings_routes import org_with_admin, published_station
    from tests.support.sittings import a_sitting

    _, admin = await org_with_admin(client, make_actor)
    issued = await client.post(
        "/api/v1/orgs/kings/scim/tokens", json={"label": "Entra"}, headers=bearer(admin)
    )
    headers = bearer(issued.json()["token"])
    created = await client.post(f"{SCIM}/Users", json=scim_user("gone@nhs.net"), headers=headers)
    trainee = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()["items"][0]
    sitting = await a_sitting(client, admin, "kings", mode="exam")
    station = await published_station(client, admin, "kings", "Chest pain")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[trainee["user_id"]],
        station_version_ids=[station],
    )

    patched = await client.patch(
        f"{SCIM}/Users/{created.json()['id']}",
        json={
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
            "Operations": [{"op": "Replace", "path": "active", "value": "False"}],
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    db_session.expire_all()
    statuses = (await db_session.execute(select(Slot.status))).scalars().all()
    assert list(statuses) == ["skipped"]
