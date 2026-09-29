"""Correcting the roster after the fact: edit, rename, remove, re-invite.

The four things the retiring client could do to an entry it had already
created, and which this API could not: change a trainee's name or intake,
rename or delete a group, rename or delete a cohort, and send the invitation
again when the first email never arrived.

`org_with_admin` is the one the circuit tests use — an owner, because
`OrgAdmin` excludes a platform admin and every write here is an
administrator's.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.notifications.models import OutboundMessage
from tests.http.test_sittings_routes import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

KINGS = "/api/v1/orgs/kings"


async def add_trainee(
    client: AsyncClient, admin: str, email: str, *, slug: str = "kings", **fields: object
) -> str:
    """Roster somebody through the door the screen uses, so the link and the
    invitation are real rather than a hand-written row."""
    body: dict[str, object] = {"email": email, **fields}
    response = await client.post(f"/api/v1/orgs/{slug}/trainees", json=body, headers=bearer(admin))
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def a_cohort(client: AsyncClient, admin: str, name: str, slug: str = "kings") -> str:
    response = await client.post(f"/api/v1/orgs/{slug}/cohorts", json={"name": name}, headers=bearer(admin))
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def a_group(client: AsyncClient, admin: str, label: str, slug: str = "kings") -> str:
    response = await client.post(
        f"/api/v1/orgs/{slug}/trainee-groups", json={"label": label}, headers=bearer(admin)
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def a_supervisor(client: AsyncClient, make_actor, org_id: uuid.UUID) -> str:  # type: ignore[no-untyped-def]
    """Somebody who may read the roster and run a circuit, but not decide it."""
    return await make_actor(
        "supervisor-kings@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )


async def invitations_to(db_session: AsyncSession, recipient: str) -> list[OutboundMessage]:
    stmt = (
        select(OutboundMessage)
        .where(OutboundMessage.template_key == "invitation", OutboundMessage.recipient == recipient)
        .order_by(OutboundMessage.available_at)
    )
    return list((await db_session.execute(stmt)).scalars())


# --------------------------------------------------------------------------
# PATCH /trainees/{id}
# --------------------------------------------------------------------------


async def test_a_roster_entry_can_be_renamed_and_moved(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """b2b's edit screen offered exactly this, and the platform had no route."""
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "misspelt@example.com", first_name="Aisha")
    cohort = await a_cohort(client, admin, "September 2026")

    edited = await client.patch(
        f"{KINGS}/trainees/{trainee}",
        json={"first_name": "Aishah", "last_name": "Nair", "cohort_id": cohort},
        headers=bearer(admin),
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["first_name"] == "Aishah"
    assert edited.json()["last_name"] == "Nair"
    assert edited.json()["cohort_id"] == cohort


async def test_an_edit_touches_only_what_was_sent(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The reason the route takes `model_fields_set` rather than the body.

    A screen that posts one field while leaving the others out of its form must
    not clear them; the legacy `PATCH /me` behaves this way for the same reason.
    """
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "March 2027")
    trainee = await add_trainee(
        client, admin, "untouched@example.com", first_name="Ben", last_name="Okafor", cohort_id=cohort
    )

    edited = await client.patch(
        f"{KINGS}/trainees/{trainee}", json={"last_name": "Okafor-Smith"}, headers=bearer(admin)
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["first_name"] == "Ben"
    assert edited.json()["last_name"] == "Okafor-Smith"
    assert edited.json()["cohort_id"] == cohort


async def test_an_explicit_null_clears_the_intake(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The edit screen's "No group" option, which needs null and absent to differ."""
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "June 2027")
    trainee = await add_trainee(client, admin, "leaver@example.com", cohort_id=cohort)

    cleared = await client.patch(
        f"{KINGS}/trainees/{trainee}", json={"cohort_id": None}, headers=bearer(admin)
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["cohort_id"] is None


async def test_an_edit_that_names_nothing_changes_nothing(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """A no-op, deliberately not the legacy's 400.

    b2b answered an empty edit with `Provide at least one of: firstName, …`,
    which is a message about the caller's form rather than about anybody on the
    roster. The platform's own `PATCH /me` treats the same request as "write
    nothing", and one rule for both partial updates beats two.
    """
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "untouched2@example.com", first_name="Ada")

    unchanged = await client.patch(f"{KINGS}/trainees/{trainee}", json={}, headers=bearer(admin))
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["first_name"] == "Ada"


async def test_an_intake_from_another_organisation_cannot_be_attached(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    outsider = await a_cohort(client, guys_admin, "Guy's intake", slug="guys")
    trainee = await add_trainee(client, kings_admin, "attached@example.com")

    refused = await client.patch(
        f"{KINGS}/trainees/{trainee}", json={"cohort_id": outsider}, headers=bearer(kings_admin)
    )
    assert refused.status_code == 404, refused.text
    assert refused.json()["code"] == "cohort_not_found"


async def test_another_orgs_trainee_cannot_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    trainee = await add_trainee(client, guys_admin, "private@example.com", slug="guys")

    refused = await client.patch(
        f"{KINGS}/trainees/{trainee}", json={"first_name": "Hijacked"}, headers=bearer(kings_admin)
    )
    assert refused.status_code == 404, refused.text
    assert refused.json()["code"] == "trainee_not_found"


async def test_a_supervisor_cannot_edit_the_roster(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "supervised@example.com")
    supervisor = await a_supervisor(client, make_actor, org_id)

    refused = await client.patch(
        f"{KINGS}/trainees/{trainee}", json={"first_name": "Nobody"}, headers=bearer(supervisor)
    )
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "forbidden"


# --------------------------------------------------------------------------
# PATCH / DELETE /trainee-groups/{id}
# --------------------------------------------------------------------------


async def test_renaming_a_group_does_not_lose_its_members(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The bug the membership table exists to prevent.

    b2b matched a trainee's cohort string against the label, so a rename either
    emptied the group or required rewriting every one of those strings.
    """
    _, admin = await org_with_admin(client, make_actor)
    group = await a_group(client, admin, "Cohort A")
    first = await add_trainee(client, admin, "keep1@example.com")
    second = await add_trainee(client, admin, "keep2@example.com")
    await client.put(
        f"{KINGS}/trainee-groups/{group}/members",
        json={"trainee_ids": [first, second]},
        headers=bearer(admin),
    )

    renamed = await client.patch(
        f"{KINGS}/trainee-groups/{group}", json={"label": "Thursday group"}, headers=bearer(admin)
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["label"] == "Thursday group"
    assert renamed.json()["member_count"] == 2

    listed = (await client.get(f"{KINGS}/trainee-groups", headers=bearer(admin))).json()
    assert [(g["label"], g["member_count"]) for g in listed["items"]] == [("Thursday group", 2)]


async def test_a_group_cannot_be_renamed_onto_another(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Two spellings of one label are one group here, and the rename says so."""
    _, admin = await org_with_admin(client, make_actor)
    await a_group(client, admin, "Cohort A")
    second = await a_group(client, admin, "Cohort B")

    refused = await client.patch(
        f"{KINGS}/trainee-groups/{second}", json={"label": "cohort   a"}, headers=bearer(admin)
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "group_exists"


async def test_a_group_with_members_does_not_vanish(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The membership rows, and anything addressed to the group, go with it."""
    _, admin = await org_with_admin(client, make_actor)
    group = await a_group(client, admin, "Busy")
    trainee = await add_trainee(client, admin, "busy-member@example.com")
    await client.put(
        f"{KINGS}/trainee-groups/{group}/members", json={"trainee_ids": [trainee]}, headers=bearer(admin)
    )

    refused = await client.delete(f"{KINGS}/trainee-groups/{group}", headers=bearer(admin))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "group_not_empty"

    emptied = await client.put(
        f"{KINGS}/trainee-groups/{group}/members", json={"trainee_ids": []}, headers=bearer(admin)
    )
    assert emptied.json()["member_count"] == 0
    removed = await client.delete(f"{KINGS}/trainee-groups/{group}", headers=bearer(admin))
    assert removed.status_code == 204, removed.text

    listed = (await client.get(f"{KINGS}/trainee-groups", headers=bearer(admin))).json()
    assert [g["id"] for g in listed["items"]] == []


async def test_another_orgs_group_cannot_be_renamed_or_removed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    group = await a_group(client, guys_admin, "Their group", slug="guys")

    renamed = await client.patch(
        f"{KINGS}/trainee-groups/{group}", json={"label": "Ours"}, headers=bearer(kings_admin)
    )
    assert renamed.status_code == 404, renamed.text
    assert renamed.json()["code"] == "group_not_found"

    removed = await client.delete(f"{KINGS}/trainee-groups/{group}", headers=bearer(kings_admin))
    assert removed.status_code == 404, removed.text
    assert removed.json()["code"] == "group_not_found"

    still_theirs = await client.get("/api/v1/orgs/guys/trainee-groups", headers=bearer(guys_admin))
    assert [g["label"] for g in still_theirs.json()["items"]] == ["Their group"]


async def test_a_supervisor_cannot_rename_or_delete_a_group(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    group = await a_group(client, admin, "Supervised")
    supervisor = await a_supervisor(client, make_actor, org_id)

    assert (
        await client.patch(f"{KINGS}/trainee-groups/{group}", json={"label": "X"}, headers=bearer(supervisor))
    ).status_code == 403
    assert (
        await client.delete(f"{KINGS}/trainee-groups/{group}", headers=bearer(supervisor))
    ).status_code == 403


# --------------------------------------------------------------------------
# PATCH / DELETE /cohorts/{id}
# --------------------------------------------------------------------------


async def test_a_cohort_can_be_renamed_without_losing_its_people(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "2026 intake")
    await add_trainee(client, admin, "in-cohort@example.com", cohort_id=cohort)

    renamed = await client.patch(
        f"{KINGS}/cohorts/{cohort}",
        json={"name": "2026 clinicals", "academic_year": "2026/27"},
        headers=bearer(admin),
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "2026 clinicals"
    assert renamed.json()["academic_year"] == "2026/27"

    roster = (await client.get(f"{KINGS}/trainees", headers=bearer(admin))).json()
    assert [t["cohort_id"] for t in roster["items"]] == [cohort]


async def test_two_cohorts_cannot_share_a_name(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`(org, name)` is unique, so the collision is a 409 and not a 500."""
    _, admin = await org_with_admin(client, make_actor)
    first = await a_cohort(client, admin, "March")
    await a_cohort(client, admin, "June")

    duplicated = await client.post(f"{KINGS}/cohorts", json={"name": "March"}, headers=bearer(admin))
    assert duplicated.status_code == 409, duplicated.text
    assert duplicated.json()["code"] == "cohort_exists"

    renamed = await client.patch(f"{KINGS}/cohorts/{first}", json={"name": "June"}, headers=bearer(admin))
    assert renamed.status_code == 409, renamed.text
    assert renamed.json()["code"] == "cohort_exists"


async def test_a_cohort_somebody_is_in_does_not_vanish(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`trainees.cohort_id` is `SET NULL`: deleting would read as those people
    never having had an intake, rather than as the mistake it is."""
    _, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "Keep me")
    trainee = await add_trainee(client, admin, "attached-too@example.com", cohort_id=cohort)

    refused = await client.delete(f"{KINGS}/cohorts/{cohort}", headers=bearer(admin))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "cohort_in_use"

    await client.patch(f"{KINGS}/trainees/{trainee}", json={"cohort_id": None}, headers=bearer(admin))
    removed = await client.delete(f"{KINGS}/cohorts/{cohort}", headers=bearer(admin))
    assert removed.status_code == 204, removed.text

    listed = (await client.get(f"{KINGS}/cohorts", headers=bearer(admin))).json()
    assert [c["id"] for c in listed["items"]] == []


async def test_another_orgs_cohort_cannot_be_renamed_or_removed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    cohort = await a_cohort(client, guys_admin, "Their intake", slug="guys")

    renamed = await client.patch(
        f"{KINGS}/cohorts/{cohort}", json={"name": "Ours"}, headers=bearer(kings_admin)
    )
    assert renamed.status_code == 404, renamed.text
    assert renamed.json()["code"] == "cohort_not_found"

    removed = await client.delete(f"{KINGS}/cohorts/{cohort}", headers=bearer(kings_admin))
    assert removed.status_code == 404, removed.text
    assert removed.json()["code"] == "cohort_not_found"


async def test_a_supervisor_cannot_rename_or_delete_a_cohort(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    cohort = await a_cohort(client, admin, "Supervised intake")
    supervisor = await a_supervisor(client, make_actor, org_id)

    assert (
        await client.patch(f"{KINGS}/cohorts/{cohort}", json={"name": "X"}, headers=bearer(supervisor))
    ).status_code == 403
    assert (await client.delete(f"{KINGS}/cohorts/{cohort}", headers=bearer(supervisor))).status_code == 403


# --------------------------------------------------------------------------
# POST /trainees/{id}/resend-invitation
# --------------------------------------------------------------------------


async def test_a_lost_invitation_can_be_sent_again(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    """The first email is one shot, and a spam folder used to end the story."""
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "lost@example.com")
    first = (await invitations_to(db_session, "lost@example.com"))[0]
    assert first is not None

    resent = await client.post(f"{KINGS}/trainees/{trainee}/resend-invitation", headers=bearer(admin))
    assert resent.status_code == 200, resent.text
    assert resent.json() == {"email": "lost@example.com", "invited_to": "Kings"}

    queued = await invitations_to(db_session, "lost@example.com")
    assert len(queued) == 2
    tokens = {str(m.payload["token"]) for m in queued}  # type: ignore[attr-defined]
    # The original link cannot be repeated — only its hash was ever stored — so
    # the re-send mints a new token, and spends the old one: two live
    # set-password links for one person is the thing a duplicate roster add
    # refuses a second invitation over.
    assert len(tokens) == 2
    newest = next(t for t in tokens if t != first.payload["token"])  # type: ignore[attr-defined]

    expired = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": str(first.payload["token"]), "password": "Str0ng-Passw0rd!"},  # type: ignore[attr-defined]
    )
    assert expired.status_code >= 400
    assert expired.json()["code"] == "invalid_reset_token"

    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": newest, "password": "Str0ng-Passw0rd!"}
    )
    assert confirmed.status_code in (200, 204), confirmed.text
    login = await client.post(
        "/api/v1/auth/login", json={"email": "lost@example.com", "password": "Str0ng-Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    assert (
        login.json()["user"]["id"]
        == (await client.get(f"{KINGS}/trainees", headers=bearer(admin))).json()["items"][0]["user_id"]
    )


async def test_somebody_who_already_joined_is_not_invited_again(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """An invitation is a set-password link; a person with a password does not
    need one and an administrator must not be able to mail them one."""
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "joined@example.com")
    queued = await invitations_to(db_session, "joined@example.com")
    await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": queued[0].payload["token"], "password": "Str0ng-Passw0rd!"},  # type: ignore[attr-defined]
    )

    refused = await client.post(f"{KINGS}/trainees/{trainee}/resend-invitation", headers=bearer(admin))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "invitation_not_pending"
    assert len(await invitations_to(db_session, "joined@example.com")) == 1


async def test_a_roster_row_left_unlinked_is_invited_and_linked(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """A row the migration carried over with no account has nothing to
    re-send, but the person still cannot sign in: so this invites them."""
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    row = await roster_repo.create_trainee(
        db_session, org_id, email="unlinked@example.com", first_name="Sam", last_name=None, cohort_id=None
    )
    await db_session.flush()
    assert await invitations_to(db_session, "unlinked@example.com") == []

    resent = await client.post(f"{KINGS}/trainees/{row.id}/resend-invitation", headers=bearer(admin))
    assert resent.status_code == 200, resent.text
    assert resent.json()["email"] == "unlinked@example.com"

    queued = await invitations_to(db_session, "unlinked@example.com")
    assert len(queued) == 1
    listed = (await client.get(f"{KINGS}/trainees", headers=bearer(admin))).json()
    entry = next(t for t in listed["items"] if t["id"] == str(row.id))
    assert entry["user_id"] is not None


async def test_another_orgs_trainee_cannot_be_sent_an_invitation(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    _, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    response = await client.post(
        "/api/v1/orgs/guys/trainees", json={"email": "theirs@example.com"}, headers=bearer(guys_admin)
    )
    assert response.status_code == 201, response.text
    theirs = response.json()["id"]

    refused = await client.post(f"{KINGS}/trainees/{theirs}/resend-invitation", headers=bearer(kings_admin))
    assert refused.status_code == 404, refused.text
    assert refused.json()["code"] == "trainee_not_found"
    assert await invitations_to(db_session, "theirs@example.com") != []


async def test_a_supervisor_cannot_resend_an_invitation(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "quiet@example.com")
    supervisor = await a_supervisor(client, make_actor, org_id)

    refused = await client.post(f"{KINGS}/trainees/{trainee}/resend-invitation", headers=bearer(supervisor))
    assert refused.status_code == 403, refused.text


async def test_a_roster_entry_nobody_examined_can_be_deleted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """No decision, so nothing for `trainee_in_use` to protect."""
    org_id, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "mistake@example.com")

    response = await client.delete(f"{KINGS}/trainees/{trainee}", headers=bearer(admin))
    assert response.status_code == 204

    gone = await client.patch(f"{KINGS}/trainees/{trainee}", json={"first_name": "x"}, headers=bearer(admin))
    assert gone.status_code == 404
    assert gone.json()["code"] == "trainee_not_found"


async def test_deleting_a_trainee_with_a_decision_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """`roster` sits below `results` in the layer contract and cannot check
    for a decision itself — the database's `RESTRICT` is the refusal,
    mapped to a clean 409 rather than a raw 500."""
    from tests.http.test_results_routes import EVIDENCE
    from tests.http.test_results_routes import a_sitting_and_trainee as a_decided_sitting_and_trainee
    from tests.http.test_results_routes import org_with_admin as org_with_institution_admin

    org_id, admin = await org_with_institution_admin(client, make_actor, "decidedorg")
    sitting, trainee = await a_decided_sitting_and_trainee(db_session, org_id)
    decided = await client.put(
        f"/api/v1/orgs/decidedorg/sittings/{sitting}/candidates/{trainee}/decision",
        json={
            "assessment_outcome": "pass",
            "rationale": "Met the standard.",
            "evidence": EVIDENCE,
            "expected_revision": 0,
        },
        headers=bearer(admin),
    )
    assert decided.status_code == 200, decided.text

    response = await client.delete(f"/api/v1/orgs/decidedorg/trainees/{trainee}", headers=bearer(admin))
    assert response.status_code == 409
    assert response.json()["code"] == "trainee_in_use"


async def test_anonymising_a_decided_trainee_scrubs_the_person_and_keeps_the_decision(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The GDPR path for exactly the row `delete` above refuses: anonymise,
    never delete, a trainee with a decision on record."""
    from tests.http.test_results_routes import EVIDENCE, a_sitting_and_named_trainee
    from tests.http.test_results_routes import org_with_admin as org_with_institution_admin

    org_id, admin = await org_with_institution_admin(client, make_actor, "gdprorg")
    sitting, trainee, original_email = await a_sitting_and_named_trainee(db_session, org_id)
    await client.put(
        f"/api/v1/orgs/gdprorg/sittings/{sitting}/candidates/{trainee}/decision",
        json={
            "assessment_outcome": "pass",
            "rationale": "Met the standard.",
            "evidence": EVIDENCE,
            "expected_revision": 0,
        },
        headers=bearer(admin),
    )

    anonymised = await client.post(
        f"/api/v1/orgs/gdprorg/trainees/{trainee}/anonymise", headers=bearer(admin)
    )
    assert anonymised.status_code == 200, anonymised.text
    body = anonymised.json()
    assert body["email"] != original_email
    assert body["first_name"] is None and body["last_name"] is None
    assert body["access_revoked"] is True
    assert body["anonymised"] is True

    # The decision itself is untouched — this is the whole point.
    kept = await client.get(
        f"/api/v1/orgs/gdprorg/sittings/{sitting}/candidates/{trainee}/decision", headers=bearer(admin)
    )
    assert kept.status_code == 200, kept.text
    assert kept.json()["assessment_outcome"] == "pass"


async def test_anonymising_twice_is_a_no_op_not_a_second_audit_row(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "twice@example.com")

    first = await client.post(f"{KINGS}/trainees/{trainee}/anonymise", headers=bearer(admin))
    assert first.status_code == 200, first.text
    scrubbed_email = first.json()["email"]

    second = await client.post(f"{KINGS}/trainees/{trainee}/anonymise", headers=bearer(admin))
    assert second.status_code == 200, second.text
    assert second.json()["email"] == scrubbed_email

    log = await client.get(f"{KINGS}/audit", headers=bearer(admin))
    assert log.status_code == 200, log.text
    anonymise_rows = [row for row in log.json()["items"] if row["action"] == "trainee.anonymised"]
    assert len(anonymise_rows) == 1


async def test_anonymising_someone_never_decided_about_still_works(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Offered unconditionally — it is `delete` that is the narrow tool here,
    not `anonymise`, since scrubbing a name never needs a `RESTRICT`'s
    protection."""
    org_id, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "mistake2@example.com")

    response = await client.post(f"{KINGS}/trainees/{trainee}/anonymise", headers=bearer(admin))
    assert response.status_code == 200, response.text
    assert response.json()["anonymised"] is True


# --------------------------------------------------------------------------
# GET /trainee-groups/{id}/members
# --------------------------------------------------------------------------


async def test_a_groups_members_can_be_read_a_page_at_a_time(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The membership screen shows names, not just the count the list returns."""
    _, admin = await org_with_admin(client, make_actor)
    group = await a_group(client, admin, "Readable")
    first = await add_trainee(client, admin, "member1@example.com")
    second = await add_trainee(client, admin, "member2@example.com")
    await add_trainee(client, admin, "outsider@example.com")
    await client.put(
        f"{KINGS}/trainee-groups/{group}/members",
        json={"trainee_ids": [first, second]},
        headers=bearer(admin),
    )

    page_one = await client.get(
        f"{KINGS}/trainee-groups/{group}/members", params={"limit": 1}, headers=bearer(admin)
    )
    assert page_one.status_code == 200, page_one.text
    assert [trainee["id"] for trainee in page_one.json()["items"]] == [first]
    cursor = page_one.json()["next_cursor"]
    assert cursor is not None

    page_two = await client.get(
        f"{KINGS}/trainee-groups/{group}/members",
        params={"limit": 1, "cursor": cursor},
        headers=bearer(admin),
    )
    assert [trainee["id"] for trainee in page_two.json()["items"]] == [second]
    assert page_two.json()["next_cursor"] is None


async def test_another_orgs_group_members_cannot_be_read(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    group = await a_group(client, guys_admin, "Theirs", slug="guys")

    refused = await client.get(f"{KINGS}/trainee-groups/{group}/members", headers=bearer(admin))
    assert refused.status_code == 404, refused.text
    assert refused.json()["code"] == "group_not_found"
