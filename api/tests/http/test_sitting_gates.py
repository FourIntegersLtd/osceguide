"""What may be scheduled and started (S-24, R-41), and whose sittings a workspace shows (T-11)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.tenancy import repository as tenancy_repo
from app.features.voice.service import get_room_agents
from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_org_read_models import a_circuit, a_sitting, a_user
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.catalog import create_exam
from tests.support.fakes import FakeRoomAgents
from tests.support.sittings import add_programme, create_sitting_body
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _schedule(client: AsyncClient, admin: str, programme_id: uuid.UUID):  # type: ignore[no-untyped-def]
    return await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name="S", programme_id=programme_id, mode="exam"),
        headers=bearer(admin),
    )


async def _set_programme(client: AsyncClient, admin: str, programme_id: uuid.UUID, status: str):  # type: ignore[no-untyped-def]
    return await client.patch(
        f"/api/v1/orgs/kings/programmes/{programme_id}", json={"status": status}, headers=bearer(admin)
    )


async def test_a_retired_programme_cannot_be_scheduled(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    assert (await _schedule(client, admin, programme_id)).status_code == 201

    retired = await _set_programme(client, admin, programme_id, "retired")
    assert (retired.status_code, retired.json()["status"]) == (200, "retired")
    refused = await _schedule(client, admin, programme_id)
    assert (refused.status_code, refused.json()["code"]) == (409, "programme_not_active")


async def test_a_draft_or_paused_programme_cannot_be_scheduled(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    draft = await add_programme(client, admin, org_slug="kings", active=False)
    refused = await _schedule(client, admin, draft)
    assert (refused.status_code, refused.json()["code"]) == (409, "programme_not_active")

    await _set_programme(client, admin, draft, "active")
    assert (await _schedule(client, admin, draft)).status_code == 201
    await _set_programme(client, admin, draft, "draft")
    paused = await _schedule(client, admin, draft)
    assert (paused.status_code, paused.json()["code"]) == (409, "programme_not_active")


async def test_a_programme_whose_exam_was_retired_cannot_be_scheduled(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    await db_session.execute(
        text("UPDATE exams SET status='retired' FROM org_programmes p WHERE p.exam_id=exams.id AND p.id=:p"),
        {"p": programme_id},
    )
    refused = await _schedule(client, admin, programme_id)
    assert (refused.status_code, refused.json()["code"]) == (409, "programme_not_active")


async def test_a_sitting_cannot_be_moved_onto_an_inactive_programme(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    root = await make_actor("root-edit@osceguide.com", platform_admin=True)
    await create_exam(client, root, code="plab")
    paused = await add_programme(client, admin, org_slug="kings", exam_code="plab", active=False)

    refused = await client.put(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}",
        json={"programme_id": str(paused)},
        headers=bearer(admin),
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "programme_not_active")


async def test_a_circuit_whose_lead_lost_the_role_cannot_start(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "cand@example.com")
    lead, _ = await an_examiner(db_session, org_id, "lead@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
        supervisor_user_id=str(lead),
    )
    for membership in await tenancy_repo.memberships_for_user_in_org(db_session, org_id, lead):
        await tenancy_repo.set_membership_role(db_session, org_id, membership.id, role="trainee")
    await db_session.flush()

    refused = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert (refused.status_code, refused.json()["code"]) == (409, "lead_cannot_run")


async def test_my_sittings_can_be_scoped_to_one_workspace(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    root = await make_actor("root-elsewhere@osceguide.com", platform_admin=True)
    other = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "elsewhere", "name": "Elsewhere", "org_type": "institution"},
        headers=bearer(root),
    )
    token = await make_actor(
        "me@example.com",
        memberships=(
            Membership(org_id=org_id, org_slug="kings", role="trainee"),
            Membership(org_id=uuid.UUID(other.json()["id"]), org_slug="elsewhere", role="trainee"),
        ),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "me@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )

    everywhere = (await client.get("/api/v1/me/sittings", headers=bearer(token))).json()
    here = (await client.get("/api/v1/me/sittings?org_slug=kings", headers=bearer(token))).json()
    there = (await client.get("/api/v1/me/sittings?org_slug=elsewhere", headers=bearer(token))).json()
    assert (len(everywhere["items"]), len(here["items"]), there["items"]) == (1, 1, [])


async def test_a_named_workspace_the_token_lacks_still_shows_rostered_sittings(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    # Rostered in kings, but this token no longer carries a kings membership.
    token = await make_actor(
        "left@example.com",
        memberships=(),
    )
    candidate_id = await a_user(db_session, "left@example.com")
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )
    scoped = await client.get("/api/v1/me/sittings?org_slug=kings", headers=bearer(token))
    nowhere = await client.get("/api/v1/me/sittings?org_slug=nowhere", headers=bearer(token))
    assert [(r.status_code, r.json()["items"]) for r in (nowhere,)] == [(200, [])]
    assert [item["id"] for item in scoped.json()["items"]] == [sitting["id"]]
    everywhere = await client.get("/api/v1/me/sittings", headers=bearer(token))
    assert [item["id"] for item in everywhere.json()["items"]] == [sitting["id"]]


async def _rostered_candidate(client, make_actor, db_session, *, start: bool = False):  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    token = await make_actor("stale@example.com", memberships=())
    candidate_id = await a_user(db_session, "stale@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )
    if start:
        await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    async def seen(query: str = "") -> list[str]:
        response = await client.get(f"/api/v1/me/sittings{query}", headers=bearer(token))
        return [item["org_slug"] for item in response.json()["items"]]

    return org_id, candidate_id, seen, token


async def _revoke_on_roster(db_session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
    from app.features.roster import repository as roster_repo

    for trainee_id in await roster_repo.trainee_ids_for_user(db_session, user_id):
        await roster_repo.set_trainee_access(db_session, org_id, trainee_id, revoked_at=datetime.now(UTC))
    await db_session.commit()


async def test_a_token_minted_before_rostering_still_sees_the_sitting(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, _, seen, _ = await _rostered_candidate(client, make_actor, db_session)
    assert (await seen(), await seen("?org_slug=kings")) == (["kings"], ["kings"])


async def test_a_trainee_revoked_on_the_roster_sees_nothing_with_or_without_a_membership_row(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """T-13 (a): the roster's revocation is the rule, as at the join gate."""
    org_id, candidate_id, seen, _ = await _rostered_candidate(client, make_actor, db_session)
    await _revoke_on_roster(db_session, org_id, candidate_id)
    assert (await seen(), await seen("?org_slug=kings")) == ([], [])


async def test_a_revoked_trainee_who_is_also_an_examiner_still_sees_no_candidate_slots(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """T-13 (b): a live staff row does not bring back the revoked candidacy."""
    org_id, candidate_id, seen, _ = await _rostered_candidate(client, make_actor, db_session)
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=candidate_id, role="examiner")
    await _revoke_on_roster(db_session, org_id, candidate_id)
    assert await seen() == []


async def test_one_live_roster_row_keeps_the_organisation_visible_and_the_gate_agrees(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.roster import service as roster_service
    from app.features.roster.models import Trainee

    org_id, candidate_id, seen, _ = await _rostered_candidate(client, make_actor, db_session)
    db_session.add(Trainee(org_id=org_id, user_id=candidate_id, email="second-row@example.com"))
    await db_session.flush()
    from app.features.roster import repository as roster_repo

    first = (await roster_repo.trainee_ids_for_user(db_session, candidate_id))[0]
    await roster_repo.set_trainee_access(db_session, org_id, first, revoked_at=datetime.now(UTC))
    await db_session.commit()
    revoked = await roster_service.is_revoked(db_session, org_id, candidate_id)
    assert (await seen(), revoked) == (
        ["kings"],
        False,
    )


async def test_a_suspension_mid_exam_lets_the_running_circuit_finish(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-17: the candidate in the room can rejoin; only new work is refused."""
    org_id, _, _, token = await _rostered_candidate(client, make_actor, db_session, start=True)
    url = "/api/v1/me/sittings"
    await tenancy_repo.set_organization_status(db_session, org_id, status="suspended")
    await db_session.commit()
    after = (await client.get(url, headers=bearer(token))).json()["items"][0]
    assert (after["slots"][0]["joinable"], after["can_join"]) == (True, True)


async def test_a_suspended_organisation_starts_no_new_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-17: not even a platform admin starts a circuit for a suspended organisation."""
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "susp@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    await tenancy_repo.set_organization_status(db_session, org_id, status="suspended")
    await db_session.flush()
    root = await make_actor("root-susp@osceguide.com", platform_admin=True)

    refused = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(root))

    assert (refused.status_code, refused.json()["code"]) == (403, "organization_suspended")


async def test_a_retired_programme_blocks_starting_and_adding_circuits_but_keeps_the_sitting(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-28: a sitting scheduled before the retirement stays, but nothing new runs under it."""
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    sitting = (await _schedule(client, admin, programme_id)).json()
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "retire@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    await _set_programme(client, admin, programme_id, "retired")

    start = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    another = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={"name": "B", "trainee_ids": [str(candidate)], "station_version_ids": [station]},
        headers=bearer(admin),
    )
    kept = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}", headers=bearer(admin))

    assert (start.status_code, start.json()["code"]) == (409, "programme_not_active")
    assert (another.status_code, another.json()["code"]) == (409, "programme_not_active")
    assert kept.status_code == 200


async def test_a_repeat_start_of_a_running_circuit_is_a_read_even_if_the_lead_was_demoted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "cand2@example.com")
    lead, _ = await an_examiner(db_session, org_id, "lead2@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
        supervisor_user_id=str(lead),
    )
    url = f"/api/v1/orgs/kings/circuits/{circuit['id']}/start"
    first = await client.post(url, headers=bearer(admin))
    assert first.status_code == 200, first.text
    for membership in await tenancy_repo.memberships_for_user_in_org(db_session, org_id, lead):
        await tenancy_repo.set_membership_role(db_session, org_id, membership.id, role="trainee")
    await db_session.flush()

    again = await client.post(url, headers=bearer(admin))
    assert (again.status_code, again.json()["started_at"]) == (200, first.json()["started_at"])


async def test_staff_can_end_a_running_circuit_in_a_suspended_organisation(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-29: a suspension lets a running circuit finish, so staff must still be able to end it."""
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "end-susp@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    started = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    assert started.status_code == 200, started.text
    await tenancy_repo.set_organization_status(db_session, org_id, status="suspended")
    await db_session.flush()

    ended = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))

    assert ended.status_code == 200, ended.text


async def test_retiring_an_exam_keeps_its_sittings_and_blocks_new_runs(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-24: same rule as a retired programme. Nothing is deleted; nothing new starts."""
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings")
    sitting = (await _schedule(client, admin, programme_id)).json()
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await a_user(db_session, "exam-retire@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    await db_session.execute(
        text("UPDATE exams SET status='retired' FROM org_programmes p WHERE p.exam_id=exams.id AND p.id=:p"),
        {"p": programme_id},
    )

    await db_session.commit()
    start = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    another = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={"name": "B", "trainee_ids": [str(candidate)], "station_version_ids": [station]},
        headers=bearer(admin),
    )
    kept = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}", headers=bearer(admin))

    assert (start.status_code, start.json()["code"]) == (409, "programme_not_active")
    assert (another.status_code, another.json()["code"]) == (409, "programme_not_active")
    assert kept.status_code == 200


async def test_ending_a_circuit_records_the_reason_in_the_audit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-19: the End dialog asks why; the reason sits beside the audit row."""
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    candidate = await a_user(db_session, "reason@example.com")
    station = await published_station(client, admin, "kings", "Chest pain")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    ended = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/end",
        json={"reason": "Fire alarm"},
        headers=bearer(admin),
    )
    log = (await client.get("/api/v1/orgs/kings/audit", headers=bearer(admin))).json()["items"]

    assert ended.status_code == 200, ended.text
    assert [r["summary"] for r in log if r["action"] == "circuit.ended"] == [
        f"Circuit {circuit['name']} ended by hand: Fire alarm"
    ]
