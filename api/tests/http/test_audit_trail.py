"""S-14: what an organisation's people and connectors do to its data leaves an audit row."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_entitlements_routes import org_with_admin as entitlement_org
from tests.http.test_org_read_models import a_circuit, a_sitting, a_user
from tests.http.test_roster_edit_routes import KINGS, add_trainee
from tests.http.test_scim_routes import SCIM, an_org_with_a_connector, scim_user
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def actions(client: AsyncClient, admin: str) -> list[str]:
    log = await client.get(f"{KINGS}/audit", headers=bearer(admin))
    assert log.status_code == 200, log.text
    return [row["action"] for row in log.json()["items"]]


async def test_revoking_restoring_and_deleting_a_trainee_are_audited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    trainee = await add_trainee(client, admin, "audit@example.com")
    for revoked in (True, False):
        done = await client.post(
            f"{KINGS}/trainees/{trainee}/access", json={"revoked": revoked}, headers=bearer(admin)
        )
        assert done.status_code == 200, done.text
    deleted = await client.delete(f"{KINGS}/trainees/{trainee}", headers=bearer(admin))
    assert deleted.status_code == 204, deleted.text
    seen = await actions(client, admin)
    assert sorted(a for a in seen if a.startswith("trainee.") and a != "trainee.added") == [
        "trainee.access_restored",
        "trainee.access_revoked",
        "trainee.deleted",
    ]


async def test_an_organisations_entitlement_grant_and_revoke_are_audited(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await entitlement_org(client, make_actor)
    await make_actor("priya@ashford.ac.uk")
    granted = await client.post(
        f"{KINGS}/entitlements",
        json={"email": "priya@ashford.ac.uk", "exam_code": "plab"},
        headers=bearer(admin),
    )
    revoked = await client.post(f"{KINGS}/entitlements/{granted.json()['id']}/revoke", headers=bearer(admin))
    assert revoked.status_code == 200, revoked.text
    assert {"entitlement.granted", "entitlement.revoked"} <= set(await actions(client, admin))


async def test_ending_a_circuit_is_audited(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    station = await published_station(client, admin, "kings", "Chest pain")
    sitting = await a_sitting(client, admin, "kings")
    candidate = await a_user(db_session, "c@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    await client.post(f"{KINGS}/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert (
        await client.post(f"{KINGS}/circuits/{circuit['id']}/end", headers=bearer(admin))
    ).status_code == 200
    again = await client.post(f"{KINGS}/circuits/{circuit['id']}/end", headers=bearer(admin))
    assert again.status_code == 200
    assert (await actions(client, admin)).count("circuit.ended") == 1


async def test_calling_off_a_sitting_is_audited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    assert (
        await client.post(f"{KINGS}/sittings/{sitting['id']}/cancel", headers=bearer(admin))
    ).status_code == 200
    assert "sitting.cancelled" in await actions(client, admin)


async def test_scim_tokens_and_connector_deactivations_are_audited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin, token = await an_org_with_a_connector(client, make_actor)
    created = await client.post(f"{SCIM}/Users", json=scim_user("ana@nhs.net"), headers=bearer(token))
    removed = await client.delete(f"{SCIM}/Users/{created.json()['id']}", headers=bearer(token))
    assert removed.status_code == 204, removed.text
    tokens = (await client.get(f"{KINGS}/scim/tokens", headers=bearer(admin))).json()
    await client.delete(f"{KINGS}/scim/tokens/{tokens[0]['id']}", headers=bearer(admin))
    log = (await client.get(f"{KINGS}/audit", headers=bearer(admin))).json()["items"]
    assert sorted(
        (r["action"], r["actor_email"]) for r in log if r["action"].startswith(("scim.", "trainee.access"))
    ) == [
        ("scim.token_issued", "admin-kings@example.com"),
        ("scim.token_revoked", "admin-kings@example.com"),
        ("trainee.access_revoked", None),
    ]


async def test_an_anonymised_trainee_is_named_nowhere_in_the_report_cohort_or_csv(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-21: the roster scrub must reach what staff download and read, not stop at the roster."""
    _, admin = await org_with_admin(client, make_actor)
    station = await published_station(client, admin, "kings", "Chest pain")
    sitting = await a_sitting(client, admin, "kings")
    candidate = await a_user(db_session, "erase.me@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    roster = await client.get(f"{KINGS}/trainees", headers=bearer(admin))
    trainee = next(t for t in roster.json()["items"] if t["email"] == "erase.me@example.com")
    gone = await client.post(f"{KINGS}/trainees/{trainee['id']}/anonymise", headers=bearer(admin))
    assert gone.status_code == 200, gone.text
    base = f"{KINGS}/sittings/{sitting['id']}"
    for path in ("report", "report.csv", "cohort"):
        page = await client.get(f"{base}/{path}", headers=bearer(admin))
        assert page.status_code == 200, (path, page.text)
        assert "erase.me" not in page.text, path
    assert "Anonymised trainee" in (await client.get(f"{base}/cohort", headers=bearer(admin))).text


async def test_publishing_a_rubric_is_audited_in_its_owners_log(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """S-14: a published marking scheme decides every later mark, so who published it is recorded."""
    from tests.support.rubrics import create_rubric

    _, admin = await org_with_admin(client, make_actor)
    root = await make_actor("root-rubric@osceguide.com", platform_admin=True)

    await create_rubric(client, admin, org_slug="kings", title="Ours")
    await create_rubric(client, root, title="Theirs")

    org_log = await client.get(f"{KINGS}/audit", headers=bearer(admin))
    platform_log = await client.get("/api/v1/platform/audit", headers=bearer(root))
    assert [r["summary"] for r in org_log.json()["items"] if r["action"] == "rubric.published"] == [
        'Published marking scheme "Ours" version 1'
    ]
    platform = [r["summary"] for r in platform_log.json()["items"] if r["action"] == "rubric.published"]
    theirs = 'Published marking scheme "Theirs" version 1'
    assert theirs in platform
    assert theirs not in [r["summary"] for r in org_log.json()["items"]]
