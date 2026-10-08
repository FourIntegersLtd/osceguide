"""The screens an institution runs, each in one request.

These are the read models the frontend is waiting on: the console replaces a
session read, a station list, a trainee list, a staff list and one feedback
probe per slot, repeated every eight seconds, and the trainee portal replaces
two lists polled every five.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.tenancy import repository as tenancy_repo
from tests.http.test_sittings_routes import (
    published_station,
)
from tests.support.catalog import create_exam
from tests.support.sittings import add_programme, org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_user(db_session: AsyncSession, email: str, *, org_slug: str = "kings") -> uuid.UUID:
    """A signed-in person, rostered into the org so a circuit may examine them.

    SEC-014 requires a circuit's candidates to be on the org's roster. These
    read-model tests build circuits directly from these ids, so this links a
    roster entry the way the real add-trainee flow does. Idempotent: called
    twice with one address it reuses the account and its roster row.
    """
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo
    from app.features.tenancy import repository as tenancy_repo

    user = await identity_repo.user_by_email(db_session, email)
    if user is None:
        user = await identity_repo.create_user(
            session=db_session, email=email, name=email, password_hash=None
        )
        await db_session.flush()
    org = await tenancy_repo.organization_by_slug(db_session, org_slug)
    if org is not None:
        already = await roster_repo.trainee_by_email(db_session, org.id, email)
        if already is None:
            trainee = await roster_repo.create_trainee(
                db_session, org.id, email=email, first_name=None, last_name=None, cohort_id=None
            )
            await roster_repo.link_trainee_to_user(db_session, org.id, trainee.id, user_id=user.id)
            await db_session.flush()
    return user.id


async def a_circuit(
    client: AsyncClient,
    admin: str,
    slug: str,
    *,
    sitting_id: str,
    trainee_ids: list[str],
    station_version_ids: list[str],
    supervisor_user_id: str | None = None,
) -> dict:
    body: dict = {
        "name": "Circuit A",
        "trainee_ids": trainee_ids,
        "station_version_ids": station_version_ids,
    }
    if supervisor_user_id:
        body["supervisor_user_id"] = supervisor_user_id
    created = await client.post(
        f"/api/v1/orgs/{slug}/sittings/{sitting_id}/circuits", json=body, headers=bearer(admin)
    )
    assert created.status_code == 201, created.text
    return created.json()


async def a_sitting(client: AsyncClient, admin: str, slug: str, *, mode: str = "exam") -> dict:
    from tests.support.sittings import add_programme, create_sitting_body

    programme_id = await add_programme(client, admin, org_slug=slug)
    created = await client.post(
        f"/api/v1/orgs/{slug}/sittings",
        json=create_sitting_body(name="Finals", programme_id=programme_id, mode=mode),
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def a_sitting_for(client: AsyncClient, admin: str, slug: str, exam_code: str) -> dict:
    from tests.support.sittings import add_programme, create_sitting_body

    programme_id = await add_programme(client, admin, org_slug=slug, exam_code=exam_code)
    created = await client.post(
        f"/api/v1/orgs/{slug}/sittings",
        json=create_sitting_body(name="First", programme_id=programme_id, mode="exam"),
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def a_library_station(
    client: AsyncClient, make_actor, *, exam_code: str = "sca", title: str = "Wheezy child"
) -> str:  # type: ignore[no-untyped-def]
    """One published platform-library station, as a platform author writes it."""
    root = await make_actor(f"library-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    await create_exam(client, root, code=exam_code)
    created = await client.post(
        "/api/v1/platform/stations",
        json={
            "title": title,
            "exam_code": exam_code,
            "content": {"who_you_are": "Ben, 6.", "why_you_came": "Noisy breathing."},
        },
        headers=bearer(root),
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"/api/v1/platform/stations/{created.json()['id']}/versions/1/publish", headers=bearer(root)
    )
    assert published.status_code == 200, published.text
    return created.json()["id"]


# --- the org dashboard -----------------------------------------------------


async def test_the_org_dashboard_counts_without_listing(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Five requests, four of them lists fetched only to be counted."""
    org_id, admin = await org_with_admin(client, make_actor)
    await a_sitting(client, admin, "kings")
    await published_station(client, admin, "kings", "Chest pain")
    await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "t1@example.com", "first_name": "Ada"},
        headers=bearer(admin),
    )

    response = await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["slug"] == "kings"
    assert body["counts"] == {
        "trainees": 1,
        "stations": 1,
        "library_stations": 0,
        "staff": 1,
        "programmes_with_markable_exam": 1,
        "sittings": 1,
    }
    assert body["setup"]["ready_to_run"] is True
    assert [s["name"] for s in body["recent_sittings"]] == ["Finals"]


async def test_a_library_only_institution_is_told_it_is_ready(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """It wrote nothing and can still examine somebody.

    The checklist counted the org's own stations, so an institution that adopted
    the platform catalogue was told to go and author cases while it was already
    running examinations against the library.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    await a_library_station(client, make_actor)
    await add_programme(client, admin, org_slug="kings")
    await client.post(
        "/api/v1/orgs/kings/trainees",
        json={"email": "lib-only@example.com", "first_name": "Ada"},
        headers=bearer(admin),
    )

    body = (await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))).json()
    assert body["counts"]["stations"] == 0
    assert body["counts"]["library_stations"] == 1
    assert body["setup"]["stations_available"] is True
    assert body["setup"]["ready_to_run"] is True


async def test_the_library_counts_only_what_is_published_for_an_exam_offered(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Two ways the number must not inflate: somebody else's draft, and an exam
    this institution does not run."""
    org_id, admin = await org_with_admin(client, make_actor)
    await add_programme(client, admin, org_slug="kings")

    root = await make_actor(f"library-{uuid.uuid4().hex[:8]}@osceguide.com", platform_admin=True)
    draft = await client.post(
        "/api/v1/platform/stations",
        json={"title": "Unpublished", "exam_code": "sca", "content": {"who_you_are": "x"}},
        headers=bearer(root),
    )
    assert draft.status_code == 201, draft.text
    await a_library_station(client, make_actor, exam_code="plab")

    body = (await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))).json()
    # Neither a draft somebody else is still writing nor a station for an exam
    # this institution does not offer is something it can run.
    assert body["counts"]["library_stations"] == 0
    assert body["setup"]["stations_available"] is False


async def test_an_empty_org_is_told_what_it_is_missing(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor, slug="empty")
    body = (await client.get("/api/v1/orgs/empty/dashboard", headers=bearer(admin))).json()
    # `org_with_admin` also publishes a platform `sca` exam and its rubric, and
    # an organisation may use those, so the two flags read true here.
    assert body["setup"] == {
        "rubric_published": True,
        "exam_published": True,
        "template_published": False,
        "sitting_scheduled": False,
        "trainees_added": False,
        "stations_available": False,
        "team_invited": False,
        "programme_exam_rubric_ready": False,
        "ready_to_run": False,
    }


async def _without_platform_catalogue(db_session: AsyncSession) -> None:
    """Take the platform's published exams, rubrics and templates out of view, until rollback."""
    from sqlalchemy import update

    from app.features.catalog.models import Exam
    from app.features.rubrics.models import RubricVersion
    from app.features.stations.models import StationTemplateVersion

    await db_session.execute(
        update(Exam).where(Exam.org_id.is_(None), Exam.status == "published").values(status="retired")
    )
    for model in (RubricVersion, StationTemplateVersion):
        await db_session.execute(
            update(model).where(model.org_id.is_(None), model.status == "published").values(status="archived")
        )


async def test_each_setup_step_turns_true_when_it_is_done(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.tenancy import repository as tenancy_repo
    from tests.http.test_org_authored_exams import author_exam, org_admin, seed_org
    from tests.http.test_roster_edit_routes import add_trainee
    from tests.http.test_station_template_routes import STRUCTURE

    org_id = await seed_org(client, make_actor, "fresh")
    admin = await org_admin(make_actor, org_id, "fresh")

    async def setup() -> dict[str, bool]:
        response = await client.get("/api/v1/orgs/fresh/dashboard", headers=bearer(admin))
        assert response.status_code == 200, response.text
        return response.json()["setup"]

    # No platform catalogue here either, so nothing is done. Retired inside this
    # test's transaction rather than assumed absent: platform rows another test
    # committed would tick three steps before the organisation did anything.
    await _without_platform_catalogue(db_session)
    assert await setup() == {
        "rubric_published": False,
        "exam_published": False,
        "template_published": False,
        "sitting_scheduled": False,
        "trainees_added": False,
        "stations_available": False,
        "team_invited": False,
        "programme_exam_rubric_ready": False,
        "ready_to_run": False,
    }

    exam = await author_exam(client, admin, "fresh", code="own", publish=False)
    assert (await setup())["rubric_published"] is True
    assert (await setup())["exam_published"] is False
    published = await client.post(f"/api/v1/orgs/fresh/exams/{exam['id']}/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    assert (await setup())["exam_published"] is True

    template = await client.post(
        "/api/v1/orgs/fresh/station-templates",
        json={"title": "Own shape", "exam_code": "own", "structure": STRUCTURE},
        headers=bearer(admin),
    )
    assert template.status_code == 201, template.text
    assert (await setup())["template_published"] is False
    await client.post(
        f"/api/v1/orgs/fresh/station-templates/{template.json()['id']}/publish", headers=bearer(admin)
    )
    assert (await setup())["template_published"] is True

    # The admin who created the organisation is not "the team".
    assert (await setup())["team_invited"] is False
    helper = await a_user(db_session, "sup-fresh@example.com", org_slug="fresh")
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=helper, role="supervisor")
    assert (await setup())["team_invited"] is True

    await add_trainee(client, admin, "t1@example.com", slug="fresh")
    assert (await setup())["trainees_added"] is True

    assert (await setup())["sitting_scheduled"] is False
    await a_sitting_for(client, admin, "fresh", "own")
    assert (await setup())["sitting_scheduled"] is True


async def test_the_org_dashboard_is_refused_to_outsiders(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    await org_with_admin(client, make_actor)
    stranger = await make_actor("stranger@example.com")
    response = await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


# --- the supervisor's list -------------------------------------------------


async def test_a_supervisor_sees_only_the_circuits_they_are_named_on(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "S1")
    supervisor_id = await a_user(db_session, "sup@example.com")
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=supervisor_id, role="supervisor")
    supervisor = await make_actor(
        "sup2@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    mine = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand1@example.com"))],
        station_version_ids=[station],
        supervisor_user_id=str(supervisor_id),
    )
    await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand2@example.com"))],
        station_version_ids=[station],
    )

    for_supervisor = await client.get(
        "/api/v1/orgs/kings/supervisor/circuits",
        headers=bearer(await _token_for(make_actor, org_id, supervisor_id)),
    )
    assert for_supervisor.status_code == 200, for_supervisor.text
    items = for_supervisor.json()["items"]
    assert [row["circuit_id"] for row in items] == [mine["id"]]
    assert items[0]["sitting_name"] == "Finals"
    assert items[0]["slot_count"] == 1
    assert items[0]["in_progress"] is False

    # Somebody else in the same org, supervising nothing, gets an empty list
    # rather than everybody's circuits.
    assert (await client.get("/api/v1/orgs/kings/supervisor/circuits", headers=bearer(supervisor))).json()[
        "items"
    ] == []


async def _token_for(make_actor, org_id: uuid.UUID, user_id: uuid.UUID) -> str:  # type: ignore[no-untyped-def]
    """A token for a user who already exists, carrying their org membership."""
    from tests.support.tokens import mint_token

    return mint_token(
        user_id=user_id,
        email="sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )


async def test_a_started_circuit_reads_as_in_progress(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "S1")
    supervisor_id = await a_user(db_session, "sup@example.com")
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=supervisor_id, role="supervisor")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
        supervisor_user_id=str(supervisor_id),
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    token = await _token_for(make_actor, org_id, supervisor_id)
    row = (await client.get("/api/v1/orgs/kings/supervisor/circuits", headers=bearer(token))).json()["items"][
        0
    ]
    assert row["in_progress"] is True
    assert row["ended"] is False


# --- the console -----------------------------------------------------------


async def test_the_console_names_every_candidate_and_station_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [
        await published_station(client, admin, "kings", "Chest pain"),
        await published_station(client, admin, "kings", "Headache"),
    ]
    # `a_user` rosters and links the candidate (SEC-014), which is what the
    # circuit's roster check needs; no separate add-trainee call is required.
    candidate = await a_user(db_session, "cand@example.com")
    supervisor_id = await a_user(db_session, "sup@example.com")
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=supervisor_id, role="supervisor")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate)],
        station_version_ids=stations,
        supervisor_user_id=str(supervisor_id),
    )

    response = await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["sitting"]["name"] == "Finals"
    assert body["sitting"]["mode"] == "exam"
    assert body["circuit"]["supervisor"]["email"] == "sup@example.com"
    assert body["circuit"]["agent_dispatched"] is False
    assert body["circuit"]["editable"] is True
    assert body["circuit"]["timing"]["simulation_minutes"] > 0

    assert [slot["station"]["title"] for slot in body["slots"]] == ["Chest pain", "Headache"]
    assert {slot["trainee"]["email"] for slot in body["slots"]} == {"cand@example.com"}
    # The roster entry is resolved from the slot's user id: two ids, one person.
    assert body["slots"][0]["trainee"]["trainee_id"] is not None
    assert all(slot["has_review"] is False for slot in body["slots"])
    assert all(slot["is_active"] is False for slot in body["slots"])


async def test_the_console_follows_the_live_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The eight-second poll: which slot is live, and in which room."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    station = await published_station(client, admin, "kings", "S1")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    slot_id = circuit["slots"][0]["id"]
    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/switch-turn",
        json={"slot_id": slot_id},
        headers=bearer(admin),
    )

    body = (
        await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    ).json()
    assert body["circuit"]["active_slot_id"] == slot_id
    assert body["circuit"]["room_name"] == f"circuit_{circuit['id']}"
    assert [slot["is_active"] for slot in body["slots"]] == [True]
    assert body["slots"][0]["room_name"] == body["circuit"]["room_name"]


async def test_the_console_refuses_another_organisations_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    other_id, other_admin = await org_with_admin(client, make_actor, slug="guys")
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "S1")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(await a_user(db_session, "cand@example.com"))],
        station_version_ids=[station],
    )

    response = await client.get(
        f"/api/v1/orgs/guys/circuits/{circuit['id']}/console", headers=bearer(other_admin)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "circuit_not_found"


# --- the trainee portal ----------------------------------------------------


async def test_a_trainee_sees_their_sittings_and_whether_to_join(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    station = await published_station(client, admin, "kings", "Chest pain")
    candidate = await make_actor(
        "me@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "me@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )

    before = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()
    assert [item["circuit_id"] for item in before["items"]] == [circuit["id"]]
    assert before["items"][0]["org_slug"] == "kings"
    assert before["items"][0]["slots"][0]["station_title"] == "Chest pain"
    # Not started: there is no room to join, and the portal must not offer one.
    assert before["items"][0]["slots"][0]["joinable"] is False

    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    after = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()
    assert after["items"][0]["slots"][0]["joinable"] is True
    assert after["items"][0]["slots"][0]["room_name"] == f"circuit_{circuit['id']}"


async def test_someone_rostered_nowhere_gets_an_empty_list(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("nobody@example.com")
    response = await client.get("/api/v1/me/sittings", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_my_sittings_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me/sittings")).status_code == 401


# --- joining, and the clock ----------------------------------------------------


async def test_the_portal_follows_the_circuit_through_its_phases(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The portal has to say which attempt is the candidate's, and where the
    clock is: the voice token is per attempt, and the clock is the circuit's.

    A candidate is in one room for the whole examination and watches the phase
    change around them, rather than waiting for a join button per station.
    """
    from datetime import datetime

    from app.features.voice.service import get_room_agents, get_voice_tokens
    from tests.support.fakes import FakeRoomAgents, FakeVoiceTokens

    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    station = await published_station(client, admin, "kings", "Chest pain")
    client._transport.app.dependency_overrides[get_voice_tokens] = lambda: FakeVoiceTokens()  # type: ignore[attr-defined]
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    candidate = await make_actor(
        "me@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    candidate_id = await a_user(db_session, "me@example.com")
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting["id"],
        trainee_ids=[str(candidate_id)],
        station_version_ids=[station],
    )
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))

    # Starting puts them straight into the reading period: there is no separate
    # act of calling the first candidate forward any more.
    before = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()["items"][0]
    assert before["phase"] == "reading"
    assert before["can_join"] is True, "the room is open before the patient arrives"
    assert before["slots"][0]["attempt_id"] is None

    advanced = await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit['id']}/advance", json={}, headers=bearer(admin)
    )
    assert advanced.status_code == 200, advanced.text

    mine = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()["items"][0]
    slot = mine["slots"][0]
    assert slot["attempt_id"] is not None
    assert mine["phase"] == "simulation"
    started = datetime.fromisoformat(mine["phase_started_at"])
    ends = datetime.fromisoformat(mine["phase_ends_at"])
    console = (
        await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    ).json()
    assert (ends - started).total_seconds() == console["circuit"]["timing"]["simulation_minutes"] * 60
    assert console["slots"][0]["attempt_id"] == slot["attempt_id"]
    assert console["slots"][0]["phase"] == "simulation"
    assert console["circuit"]["phase"] == "simulation"

    # The candidate can ask for the room by the circuit, without naming an
    # attempt or an organisation at all.
    token = await client.post(f"/api/v1/me/circuits/{circuit['id']}/join-token", headers=bearer(candidate))
    assert token.status_code == 200, token.text

    # It was the only station, so the consultation ending ends the circuit and
    # the clock comes off with it.
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/advance", json={}, headers=bearer(admin))
    after = (await client.get("/api/v1/me/sittings", headers=bearer(candidate))).json()["items"][0]
    assert after["phase"] is None
    assert after["live"] is False
    # The recording survives the circuit it was made in: it is what gets marked.
    assert after["slots"][0]["attempt_id"] == slot["attempt_id"]


async def test_the_clock_moves_between_stations_without_anybody_switching_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """What `switch-turn` and `dispatch-agent` used to do by hand, in order.

    Two things had to be true of those and remain true of this: one candidate
    holds the clock at a time, and the one who had it loses it. Two screens
    showing two deadlines is the failure, and it is the reason the clock moved
    onto the circuit — with one row holding it, it cannot happen at all.
    """
    from app.features.voice.service import get_room_agents
    from tests.support.fakes import FakeRoomAgents

    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")
    stations = [
        await published_station(client, admin, "kings", "S1"),
        await published_station(client, admin, "kings", "S2"),
    ]
    trainees = [str(await a_user(db_session, f"t{i}@example.com")) for i in (1, 2)]
    circuit = await a_circuit(
        client, admin, "kings", sitting_id=sitting["id"], trainee_ids=trainees, station_version_ids=stations
    )
    client._transport.app.dependency_overrides[get_room_agents] = lambda: FakeRoomAgents()  # type: ignore[attr-defined]
    await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/start", headers=bearer(admin))
    slots = circuit["slots"]

    def console_slots(payload: dict) -> dict:  # type: ignore[type-arg]
        return {s["id"]: s for s in payload["slots"]}

    first = (
        await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    ).json()
    assert console_slots(first)[slots[0]["id"]]["phase"] == "reading"
    assert console_slots(first)[slots[1]["id"]]["phase"] is None

    url = f"/api/v1/orgs/kings/circuits/{circuit['id']}/advance"
    await client.post(url, json={}, headers=bearer(admin))  # into the consultation
    await client.post(url, json={}, headers=bearer(admin))  # on to the next station

    console = (
        await client.get(f"/api/v1/orgs/kings/circuits/{circuit['id']}/console", headers=bearer(admin))
    ).json()
    by_id = console_slots(console)
    assert by_id[slots[0]["id"]]["phase"] is None, "the clock left with them"
    assert by_id[slots[0]["id"]]["status"] == "completed"
    assert by_id[slots[1]["id"]]["phase"] == "reading"
    assert console["circuit"]["active_slot_id"] == slots[1]["id"]

    ended = await client.post(f"/api/v1/orgs/kings/circuits/{circuit['id']}/end", headers=bearer(admin))
    assert all(s["phase"] is None for s in ended.json()["slots"])


async def test_a_draft_programme_does_not_count_as_ready(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """B-3: setup ticked "programme ready" for a draft nobody can sit; activating it ticks it."""
    _, admin = await org_with_admin(client, make_actor)
    programme_id = await add_programme(client, admin, org_slug="kings", active=False)

    draft = (await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))).json()
    assert draft["counts"]["programmes_with_markable_exam"] == 0
    assert draft["setup"]["programme_exam_rubric_ready"] is False

    await client.patch(
        f"/api/v1/orgs/kings/programmes/{programme_id}", json={"status": "active"}, headers=bearer(admin)
    )
    active = (await client.get("/api/v1/orgs/kings/dashboard", headers=bearer(admin))).json()
    assert active["counts"]["programmes_with_markable_exam"] == 1
    assert active["setup"]["programme_exam_rubric_ready"] is True
