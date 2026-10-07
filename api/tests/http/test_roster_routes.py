"""Rostering, and the group membership b2b does not store."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
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
    # Nothing is seeded, so the exam an org's stations name has to be written
    # first — by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def add_trainee(client: AsyncClient, admin: str, email: str, slug: str = "kings") -> str:
    response = await client.post(
        f"/api/v1/orgs/{slug}/trainees", json={"email": email}, headers=bearer(admin)
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_a_trainee_is_added_and_listed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    await add_trainee(client, admin, "alice@example.com")
    response = await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))
    assert [t["email"] for t in response.json()["items"]] == ["alice@example.com"]


async def test_the_same_email_twice_conflicts(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    """And does not invite them twice: rostering an unknown address mints a
    set-password token, so a second one would leave two live links out."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    _, admin = await org_with_admin(client, make_actor)
    await add_trainee(client, admin, "dupe@example.com")
    response = await client.post(
        "/api/v1/orgs/kings/trainees", json={"email": "DUPE@example.com"}, headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "trainee_exists"

    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
    assert [m.recipient for m in (await db_session.execute(stmt)).scalars()] == ["dupe@example.com"]


async def test_access_can_be_revoked_and_restored(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee_id = await add_trainee(client, admin, "revoke@example.com")

    revoked = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access",
        json={"revoked": True},
        headers=bearer(admin),
    )
    assert revoked.json()["access_revoked"] is True

    restored = await client.post(
        f"/api/v1/orgs/kings/trainees/{trainee_id}/access",
        json={"revoked": False},
        headers=bearer(admin),
    )
    assert restored.json()["access_revoked"] is False


async def test_group_membership_is_stored_not_matched(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """b2b matches a trainee's cohort string against a group's label. Here the
    membership is a row, so renaming the group changes nothing about who is in it."""
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post(
            "/api/v1/orgs/kings/trainee-groups",
            json={"label": "Cohort A"},
            headers=bearer(admin),
        )
    ).json()
    first = await add_trainee(client, admin, "g1@example.com")
    second = await add_trainee(client, admin, "g2@example.com")

    response = await client.put(
        f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members",
        json={"trainee_ids": [first, second]},
        headers=bearer(admin),
    )
    assert response.status_code == 200
    assert response.json()["member_count"] == 2


async def test_two_spellings_of_a_label_are_one_group(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "Cohort A"}, headers=bearer(admin))
    response = await client.post(
        "/api/v1/orgs/kings/trainee-groups", json={"label": "  cohort   a "}, headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "group_exists"


async def test_setting_members_replaces_them(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "G"}, headers=bearer(admin))
    ).json()
    first = await add_trainee(client, admin, "r1@example.com")
    second = await add_trainee(client, admin, "r2@example.com")
    url = f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members"

    await client.put(url, json={"trainee_ids": [first, second]}, headers=bearer(admin))
    replaced = await client.put(url, json={"trainee_ids": [first]}, headers=bearer(admin))
    assert replaced.json()["member_count"] == 1


async def test_a_trainee_from_another_org_cannot_be_added(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    outsider = await add_trainee(client, guys_admin, "outsider@example.com", slug="guys")
    group = (
        await client.post(
            "/api/v1/orgs/kings/trainee-groups", json={"label": "G"}, headers=bearer(kings_admin)
        )
    ).json()

    response = await client.put(
        f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members",
        json={"trainee_ids": [outsider]},
        headers=bearer(kings_admin),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "trainee_not_found"


async def test_resolving_a_roster_merges_explicit_and_group_members(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "G"}, headers=bearer(admin))
    ).json()
    named = await add_trainee(client, admin, "named@example.com")
    member = await add_trainee(client, admin, "member@example.com")
    await client.put(
        f"/api/v1/orgs/kings/trainee-groups/{group['id']}/members",
        json={"trainee_ids": [member]},
        headers=bearer(admin),
    )

    response = await client.post(
        "/api/v1/orgs/kings/roster/resolve",
        json={"trainee_ids": [named], "group_ids": [group["id"]]},
        headers=bearer(admin),
    )
    assert response.json()["trainee_ids"] == [named, member]
    assert response.json()["warnings"] == []


async def test_an_empty_linked_group_is_reported(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The warning is what stops an examination starting without half its
    candidates."""
    _, admin = await org_with_admin(client, make_actor)
    group = (
        await client.post("/api/v1/orgs/kings/trainee-groups", json={"label": "Empty"}, headers=bearer(admin))
    ).json()
    response = await client.post(
        "/api/v1/orgs/kings/roster/resolve",
        json={"trainee_ids": [], "group_ids": [group["id"]]},
        headers=bearer(admin),
    )
    assert response.json()["trainee_ids"] == []
    assert response.json()["warnings"] == [{"code": "empty_group", "group_id": group["id"]}]


async def test_another_orgs_roster_is_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    await add_trainee(client, kings_admin, "private@example.com")
    response = await client.get("/api/v1/orgs/guys/trainees", headers=bearer(guys_admin))
    assert response.json()["items"] == []


async def test_rostering_somebody_who_already_has_an_account_links_them(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """`trainees.user_id` was modelled and never written by anything.

    A slot names a `users.id`; a released result is keyed on `trainees.id`.
    Without the link they are two unconnected records for one person.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    await make_actor("already@example.com")

    created = await client.post(
        "/api/v1/orgs/kings/trainees", json={"email": "already@example.com"}, headers=bearer(admin)
    )
    assert created.status_code == 201, created.text
    assert created.json()["user_id"] is not None


async def test_rostering_an_unknown_address_invites_them(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    """The usual order: an institution rosters by email before the person has an account.

    The account is created and linked in the same call, and the person is
    emailed a link to choose a password. A slot names a `users.id`, so until
    this a rostered student with no account could not be scheduled at all.
    """
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    org_id, admin = await org_with_admin(client, make_actor)
    created = await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "invited@example.com", "first_name": "Priya", "last_name": "Nair"},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    assert created.json()["user_id"] is not None

    queued = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
            )
        ).scalars()
    )
    assert [m.recipient for m in queued] == ["invited@example.com"]
    assert queued[0].payload["invited_to"] == "Kings"

    # The invitation token is an ordinary reset token: choosing a password
    # goes through the route that already exists for that.
    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": queued[0].payload["token"], "password": "Str0ng-Passw0rd!"},
    )
    assert confirmed.status_code in (200, 204), confirmed.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": "invited@example.com", "password": "Str0ng-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["id"] == created.json()["user_id"]
    assert login.json()["user"]["must_change_password"] is False


async def test_an_invited_account_cannot_sign_in_before_choosing_a_password(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    await add_trainee(client, admin, "locked@example.com")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "locked@example.com", "password": "anything-at-all"}
    )
    assert login.status_code == 401
    assert login.json()["code"] == "invalid_credentials"


async def test_registering_claims_a_roster_entry_left_unlinked(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """A row with no account — as the migration leaves them — is claimed on registration."""
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    row = await roster_repo.create_trainee(
        db_session, org_id, email="legacy@example.com", first_name=None, last_name=None, cohort_id=None
    )
    await db_session.flush()

    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "legacy@example.com", "name": "Legacy", "password": "Str0ng-Passw0rd!"},
    )
    assert registered.status_code in (200, 201), registered.text
    user_id = registered.json()["user"]["id"]

    listed = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()
    entry = next(r for r in listed["items"] if r["id"] == str(row.id))
    assert entry["user_id"] == user_id


async def test_the_roster_can_be_searched_by_name_email_or_cohort(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    cohort = (
        await client.post("/api/v1/orgs/kings/cohorts", json={"name": "2027 intake"}, headers=bearer(admin))
    ).json()
    await client.post(
        "/api/v1/orgs/kings/trainees",
        json={
            "email": "priya@example.com",
            "first_name": "Priya",
            "last_name": "Nair",
            "cohort_id": cohort["id"],
        },
        headers=bearer(admin),
    )
    await add_trainee(client, admin, "unrelated@example.com")

    by_name = await client.get(
        "/api/v1/orgs/kings/trainees", params={"search": "priya"}, headers=bearer(admin)
    )
    assert [t["email"] for t in by_name.json()["items"]] == ["priya@example.com"]

    by_email = await client.get(
        "/api/v1/orgs/kings/trainees", params={"search": "PRIYA@example.com"}, headers=bearer(admin)
    )
    assert [t["email"] for t in by_email.json()["items"]] == ["priya@example.com"]

    by_cohort = await client.get(
        "/api/v1/orgs/kings/trainees", params={"search": "2027"}, headers=bearer(admin)
    )
    assert [t["email"] for t in by_cohort.json()["items"]] == ["priya@example.com"]

    no_match = await client.get(
        "/api/v1/orgs/kings/trainees", params={"search": "nobody-like-this"}, headers=bearer(admin)
    )
    assert no_match.json()["items"] == []


async def test_a_spreadsheet_is_rostered_in_one_request(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Duplicates are reported, not fatal: one bad row must not refuse the cohort."""
    _, admin = await org_with_admin(client, make_actor)
    await add_trainee(client, admin, "already@example.com")

    response = await client.post(
        "/api/v1/orgs/kings/trainees/bulk",
        json={
            "trainees": [
                {"email": "one@example.com", "first_name": "One"},
                {"email": "two@example.com", "first_name": "Two"},
                {"email": "ALREADY@example.com"},
                {"email": "One@example.com"},
            ]
        },
        headers=bearer(admin),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert [t["email"] for t in body["created"]] == ["one@example.com", "two@example.com"]
    assert all(t["user_id"] is not None for t in body["created"])
    assert body["skipped"] == [
        {"email": "ALREADY@example.com", "code": "trainee_exists"},
        {"email": "One@example.com", "code": "trainee_exists"},
    ]

    listed = (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(admin))).json()
    assert len(listed["items"]) == 3


async def test_an_empty_upload_is_invalid(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/trainees/bulk", json={"trainees": []}, headers=bearer(admin)
    )
    assert response.status_code == 422


async def test_an_import_over_the_limit_names_the_limit(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """B-7: 501 rows answered "The request was not valid"; the refusal now says 500."""
    _, admin = await org_with_admin(client, make_actor)
    rows = [{"email": f"t{index}@example.com"} for index in range(501)]
    response = await client.post(
        "/api/v1/orgs/kings/trainees/bulk", json={"trainees": rows}, headers=bearer(admin)
    )
    assert response.status_code == 422
    assert response.json()["code"] == "too_many_trainees"
    assert response.json()["message"] == (
        "An import takes at most 500 trainees at a time; this one had 501. Send the rest in another import."
    )


async def test_the_roster_filters_on_revoked_access(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    revoked_id = await add_trainee(client, admin, "gone@example.com")
    await add_trainee(client, admin, "still-here@example.com")
    await client.post(
        f"/api/v1/orgs/kings/trainees/{revoked_id}/access", json={"revoked": True}, headers=bearer(admin)
    )

    revoked = await client.get("/api/v1/orgs/kings/trainees?access_revoked=true", headers=bearer(admin))
    active = await client.get("/api/v1/orgs/kings/trainees?access_revoked=false", headers=bearer(admin))
    assert [trainee["email"] for trainee in revoked.json()["items"]] == ["gone@example.com"]
    assert [trainee["email"] for trainee in active.json()["items"]] == ["still-here@example.com"]
