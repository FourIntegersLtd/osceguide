"""Two things a station's users hit: building a circuit for a platform exam, and withdrawing a
version something still depends on."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity import repository as identity_repo
from app.features.station_sets.models import StationSet, StationSetEntry
from app.features.stations.models import Station, StationVersion
from tests.http.test_stations_routes import a_library_station, make_station, member, seed_org
from tests.support.sittings import add_programme
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_org_staff_browse_the_platform_library_of_an_exam_their_org_offers(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The circuit builder reads the platform leg as the organisation, not as a consumer.

    The staff member holds no entitlement and no exam of their own; the organisation's programme
    for the exam is what lets them see its stations, and an organisation that does not offer it
    is still refused.
    """
    org_id = await seed_org(client, make_actor)
    owner = await member(make_actor, org_id, "kings", "owner")
    await a_library_station(db_session, "Chest pain")
    other_org = await seed_org(client, make_actor, slug="elsewhere")
    outsider = await member(make_actor, other_org, "elsewhere", "owner")
    await add_programme(client, owner, org_slug="kings", exam_code="sca")

    allowed = await client.get("/api/v1/stations", params={"exam_code": "sca"}, headers=bearer(owner))
    refused = await client.get("/api/v1/stations", params={"exam_code": "sca"}, headers=bearer(outsider))

    assert allowed.status_code == 200, allowed.text
    assert [row["title"] for row in allowed.json()["items"]] == ["Chest pain"]
    assert refused.status_code == 403
    assert refused.json()["code"] == "not_entitled"


async def test_a_version_in_a_practice_set_cannot_be_archived(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Archiving would leave the set's entry refused `station_not_published` the next time it opens."""
    org_id = await seed_org(client, make_actor)
    owner = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, owner)
    base = f"/api/v1/orgs/kings/stations/{station['id']}/versions/1"
    assert (await client.post(f"{base}/publish", headers=bearer(owner))).status_code == 200
    version = (
        await db_session.execute(select(StationVersion).where(StationVersion.station_id == station["id"]))
    ).scalar_one()
    user = await identity_repo.user_by_email(db_session, "owner-kings@example.com")
    assert user is not None
    exam_id = (
        await db_session.execute(select(Station.exam_id).where(Station.id == station["id"]))
    ).scalar_one()
    practice_set = StationSet(owner_user_id=user.id, exam_id=exam_id, name="Mine")
    db_session.add(practice_set)
    await db_session.flush()
    db_session.add(StationSetEntry(set_id=practice_set.id, position=0, station_version_id=version.id))
    await db_session.flush()
    await db_session.commit()

    response = await client.post(f"{base}/archive", headers=bearer(owner))

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "not_archivable"
    assert response.json()["details"] == {"reason": "in_use", "circuits": 0, "sets": 1}


async def _publish_and_put_on_a_circuit(
    client: AsyncClient, make_actor, db_session: AsyncSession, *, ended: bool
):  # type: ignore[no-untyped-def]
    """An org's published station on a circuit, finished or not; returns (headers, archive url)."""
    from datetime import UTC, datetime

    from app.features.sittings.models import Circuit, CircuitStation, Sitting
    from tests.support.rubrics import published_feedback_version

    org_id = await seed_org(client, make_actor)
    owner = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, owner)
    base = f"/api/v1/orgs/kings/stations/{station['id']}/versions/1"
    assert (await client.post(f"{base}/publish", headers=bearer(owner))).status_code == 200
    version_id = (
        await db_session.execute(select(StationVersion.id).where(StationVersion.station_id == station["id"]))
    ).scalar_one()
    rubric_version = await published_feedback_version(db_session, org_id)
    sitting = Sitting(org_id=org_id, name="S", mode="exam", rubric_version_id=rubric_version.id)
    db_session.add(sitting)
    await db_session.flush()
    circuit = Circuit(
        org_id=org_id, sitting_id=sitting.id, name="C", ended_at=datetime.now(UTC) if ended else None
    )
    db_session.add(circuit)
    await db_session.flush()
    db_session.add(CircuitStation(circuit_id=circuit.id, position=0, station_version_id=version_id))
    await db_session.commit()
    return bearer(owner), f"{base}/archive"


async def test_a_version_on_an_unfinished_circuit_cannot_be_archived(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    headers, url = await _publish_and_put_on_a_circuit(client, make_actor, db_session, ended=False)

    response = await client.post(url, headers=headers)

    assert response.status_code == 409, response.text
    assert response.json()["details"] == {"reason": "in_use", "circuits": 1, "sets": 0}


async def test_a_version_only_on_an_ended_circuit_can_be_archived(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    headers, url = await _publish_and_put_on_a_circuit(client, make_actor, db_session, ended=True)

    response = await client.post(url, headers=headers)

    assert response.status_code == 200, response.text
