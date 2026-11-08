"""Correcting a sitting after it has been scheduled.

Oracle: `b2b-api/app/features/sessions/service.py::update_session` and its edit
screen, `frontend/src/b2b/components/features/sessions/pages/OrgSessionEditPage.tsx`
— which offered a name, a type and a feedback template, warned "You can still
rename the session; changing type or feedback template is blocked" once anything
was live, and answered a blocked change with a conflict. The template is not a
field on a sitting here: it is resolved from the programme, so the programme is
the field that carries it.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.catalog import create_exam
from tests.support.fakes import FakeRoomAgents
from tests.support.sittings import (
    a_trainee,
    add_programme,
    create_sitting_body,
    org_with_admin,
    published_station,
)
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    """A patient that never reaches LiveKit. Starting a circuit touches the room."""
    from app.features.voice.service import get_room_agents

    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def a_sitting(client: AsyncClient, admin: str, *, name: str = "Finals", mode: str = "exam") -> dict:  # type: ignore[type-arg]
    """A sitting on the org's SCA programme, as the create screen writes one."""
    programme_id = await add_programme(client, admin, org_slug="kings")
    created = await client.post(
        "/api/v1/orgs/kings/sittings",
        json=create_sitting_body(name=name, programme_id=programme_id, mode=mode),
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def a_circuit(client: AsyncClient, db_session: AsyncSession, admin: str, sitting_id: str) -> dict:  # type: ignore[type-arg]
    """One candidate, one station — a circuit that is legal in both modes."""
    station = await published_station(client, admin, "kings", "Chest pain")
    created = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(await a_trainee(db_session, f"c-{uuid.uuid4().hex[:6]}@example.com"))],
            "station_version_ids": [station],
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    return created.json()


async def started(client: AsyncClient, admin: str, circuit_id: str) -> None:
    response = await client.post(f"/api/v1/orgs/kings/circuits/{circuit_id}/start", headers=bearer(admin))
    assert response.status_code == 200, response.text


async def edit(client: AsyncClient, admin: str, sitting_id: str, body: dict):  # type: ignore[no-untyped-def,type-arg]
    return await client.put(f"/api/v1/orgs/kings/sittings/{sitting_id}", json=body, headers=bearer(admin))


# --- what an edit may write -------------------------------------------------


async def test_a_sitting_can_be_renamed_and_re_dated(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The legacy screen's whole point, and the half of it that never freezes."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)

    edited = await edit(
        client, admin, sitting["id"], {"name": "Finals, Michaelmas", "scheduled_for": "2027-01-12T09:00:00Z"}
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Finals, Michaelmas"
    assert edited.json()["scheduled_for"].startswith("2027-01-12T09:00:00")


async def test_an_absent_field_is_left_alone(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """A PUT of what one screen holds is not a PUT of the whole sitting.

    The legacy route dumped its body with `exclude_unset` before writing it, so a
    field the screen did not carry survived the save. Sending the whole dump
    there would have nulled the date on every rename, and the same is true here.
    """
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    await edit(client, admin, sitting["id"], {"scheduled_for": "2027-01-12T09:00:00Z"})

    edited = await edit(client, admin, sitting["id"], {"name": "Renamed"})

    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Renamed"
    assert edited.json()["scheduled_for"].startswith("2027-01-12"), "the date was not the field being edited"


async def test_clearing_the_date_is_a_request_and_not_an_absence(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """ "Not scheduled" is a state a sitting can be in, so it has to be sayable."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    await edit(client, admin, sitting["id"], {"scheduled_for": "2027-01-12T09:00:00Z"})

    edited = await edit(client, admin, sitting["id"], {"name": "Unscheduled", "scheduled_for": None})

    assert edited.status_code == 200, edited.text
    assert edited.json()["scheduled_for"] is None


async def test_putting_back_an_unchanged_document_changes_nothing(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """Including with an empty body, which is a form nobody edited, not a bad one."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)

    edited = await edit(client, admin, sitting["id"], {})

    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == sitting["name"]
    assert edited.json()["mode"] == sitting["mode"]


async def test_the_type_of_an_empty_sitting_can_still_be_changed(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The mistake the route exists to correct, while there is nothing to break."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, mode="training")

    edited = await edit(client, admin, sitting["id"], {"mode": "exam", "sitting_type": "mock_exam"})

    assert edited.status_code == 200, edited.text
    assert edited.json()["mode"] == "exam"
    assert edited.json()["sitting_type"] == "mock_exam"


# --- what an edit may not ---------------------------------------------------


async def test_the_mode_of_a_sitting_with_circuits_is_frozen(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The mode is what a circuit's slots are composed from.

    Flipping it over the top of circuits already built would leave a sitting
    labelled `exam` holding a training rotation, and every route that reads the
    sitting's mode — `append-trainees` above all — would then be wrong about
    them. b2b let this through because its circuits were mode-independent JSON.
    """
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, mode="training")
    await a_circuit(client, db_session, admin, sitting["id"])

    edited = await edit(client, admin, sitting["id"], {"mode": "exam"})

    assert edited.status_code == 409, edited.text
    assert edited.json()["code"] == "invalid_circuit"


async def test_a_begun_sitting_cannot_be_retyped(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The freeze the route is built around: nothing already examined moves."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    circuit = await a_circuit(client, db_session, admin, sitting["id"])
    await started(client, admin, circuit["id"])

    edited = await edit(client, admin, sitting["id"], {"sitting_type": "mock_exam"})

    assert edited.status_code == 409, edited.text
    assert edited.json()["code"] == "sitting_locked"


async def test_a_begun_sitting_can_still_be_renamed(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """What the legacy screen said in its own words, and what the freeze must not eat."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    circuit = await a_circuit(client, db_session, admin, sitting["id"])
    await started(client, admin, circuit["id"])

    edited = await edit(
        client, admin, sitting["id"], {"name": "Room changed at the last minute", "scheduled_for": None}
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Room changed at the last minute"


async def test_restating_a_frozen_field_is_not_changing_it(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """A screen that PUTs the whole document back has not edited the mode.

    Without this the freeze becomes "a begun sitting cannot be saved at all",
    which is what comparing the *sent* fields against the frozen set does — and
    the legacy client sent every field it held on each save.
    """
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    circuit = await a_circuit(client, db_session, admin, sitting["id"])
    await started(client, admin, circuit["id"])

    edited = await edit(
        client,
        admin,
        sitting["id"],
        {"name": "Renamed", "mode": sitting["mode"], "sitting_type": sitting["sitting_type"]},
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["name"] == "Renamed"


# --- the rubric, which travels with the programme ---------------------------


async def test_moving_the_programme_moves_the_rubric_it_is_marked_against(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The legacy "change the feedback template", said this backend's way.

    A sitting's rubric is not chosen per sitting; it is resolved from the
    programme's exam. So moving the programme has to re-resolve the binding in
    the same write, or the sitting would be marked against a document belonging
    to an exam it no longer offers.
    """
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    root = await make_actor(f"root-{uuid.uuid4().hex[:6]}@osceguide.com", platform_admin=True)
    await create_exam(client, root, code="plab")
    plab_programme = await add_programme(client, admin, org_slug="kings", exam_code="plab")

    edited = await edit(client, admin, sitting["id"], {"programme_id": str(plab_programme)})

    assert edited.status_code == 200, edited.text
    assert edited.json()["programme_id"] == str(plab_programme)
    assert edited.json()["rubric_version_id"] != sitting["rubric_version_id"]


async def test_a_programme_that_cannot_be_marked_against_is_refused(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The re-binding goes through the gate a new sitting already goes through."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)

    edited = await edit(
        client, admin, sitting["id"], {"programme_id": "00000000-0000-0000-0000-000000000000"}
    )

    assert edited.status_code == 404, edited.text
    assert edited.json()["code"] == "programme_not_found"


# --- who may edit -----------------------------------------------------------


async def test_an_administrator_of_another_organisation_cannot_edit_it(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """404, not 403: the sitting is not theirs to be told about."""
    _, kings = await org_with_admin(client, make_actor, "kings")
    _, guys = await org_with_admin(client, make_actor, "guys")
    sitting = await a_sitting(client, kings)

    edited = await client.put(
        f"/api/v1/orgs/guys/sittings/{sitting['id']}", json={"name": "Ours now"}, headers=bearer(guys)
    )

    assert edited.status_code == 404, edited.text
    assert edited.json()["code"] == "sitting_not_found"


async def test_a_supervisor_cannot_edit_a_sitting(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """Running an examination is not the standing that schedules one."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    supervisor = await make_actor(
        "sup-edit@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    edited = await client.put(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}", json={"name": "Mine now"}, headers=bearer(supervisor)
    )

    assert edited.status_code == 403, edited.text


async def test_a_trainee_cannot_edit_a_sitting_they_are_sitting(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    trainee = await make_actor(
        "trainee-edit@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    edited = await client.put(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}",
        json={"name": "Everyone passes"},
        headers=bearer(trainee),
    )

    assert edited.status_code == 403, edited.text


async def test_an_org_station_never_waits_on_platform_approval(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """`approved` gates the platform library only: an org's published station is listed, picked and run."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin)
    version_id = await published_station(client, admin, "kings", "Chest pain")

    listed = await client.get("/api/v1/orgs/kings/stations", headers=bearer(admin))
    assert listed.status_code == 200, listed.text
    rows = listed.json()["items"] if isinstance(listed.json(), dict) else listed.json()
    assert [(row["status"], row["approved"]) for row in rows] == [("published", False)]

    circuit = await client.post(
        f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
        json={
            "name": "Room 1",
            "trainee_ids": [str(await a_trainee(db_session, "unapproved@example.com"))],
            "station_version_ids": [version_id],
        },
        headers=bearer(admin),
    )
    assert circuit.status_code == 201, circuit.text
