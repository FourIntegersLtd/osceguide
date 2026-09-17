"""The station lifecycle over HTTP, and who may drive it."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from tests.support.catalog import create_exam, ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CONTENT = {"patient_information": {"persona": "anxious"}, "doctor_information": {"task": "assess"}}


async def seed_org(client: AsyncClient, make_actor, slug: str = "kings") -> uuid.UUID:  # type: ignore[no-untyped-def]
    token = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    # Nothing is seeded, so the exam an org's stations name has to be written
    # first — by a platform admin, which is exactly who is holding this token.
    await create_exam(client, token, code="sca")
    return uuid.UUID(response.json()["id"])


async def member(make_actor, org_id: uuid.UUID, slug: str, role: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"{role}-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role=role),),
        active_org_slug=slug,
    )


async def make_station(client: AsyncClient, token: str, slug: str = "kings") -> dict:
    response = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": "Chest pain", "exam_code": "sca", "content": CONTENT},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Authoring
# --------------------------------------------------------------------------


async def test_an_admin_creates_a_station_as_a_draft(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    station = await make_station(client, await member(make_actor, org_id, "kings", "owner"))
    assert station["status"] == "draft"
    assert station["version"] == 1
    assert station["owner_kind"] == "org"


async def test_a_trainee_may_not_author_a_station(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "Chest pain", "exam_code": "sca", "content": CONTENT},
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 403


async def test_a_station_needs_a_known_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    response = await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "X", "exam_code": "mrcp", "content": CONTENT},
        headers=bearer(await member(make_actor, org_id, "kings", "owner")),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------


async def test_publishing_a_draft_makes_it_usable(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "published"


async def test_publishing_twice_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    url = f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish"
    await client.post(url, headers=bearer(token))
    response = await client.post(url, headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "already_published"


async def test_a_published_version_cannot_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It is what past attempts were assessed against."""
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1",
        json={"content": {"changed": True}},
        headers=bearer(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_editable"


async def test_a_draft_may_be_edited(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1",
        json={"content": {"patient_information": {"persona": "calm"}}},
        headers=bearer(token),
    )
    assert response.status_code == 200


async def test_a_new_version_is_seeded_from_the_published_one(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions", headers=bearer(token)
    )
    assert response.status_code == 201
    assert response.json()["version"] == 2
    assert response.json()["status"] == "draft"
    assert response.json()["content"] == CONTENT


async def test_archiving_needs_a_published_version(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/archive", headers=bearer(token)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_archivable"


# --------------------------------------------------------------------------
# Listing and isolation
# --------------------------------------------------------------------------


async def test_an_org_sees_its_own_stations(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    await make_station(client, token)
    response = await client.get("/api/v1/orgs/kings/stations", headers=bearer(token))
    assert response.status_code == 200
    assert [s["title"] for s in response.json()["items"]] == ["Chest pain"]


async def test_another_orgs_stations_are_invisible(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    kings = await seed_org(client, make_actor, "kings")
    guys = await seed_org(client, make_actor, "guys")
    await make_station(client, await member(make_actor, kings, "kings", "owner"))
    response = await client.get(
        "/api/v1/orgs/guys/stations", headers=bearer(await member(make_actor, guys, "guys", "owner"))
    )
    assert response.json()["items"] == []


async def test_a_trainee_may_browse_stations(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    await make_station(client, await member(make_actor, org_id, "kings", "owner"))
    response = await client.get(
        "/api/v1/orgs/kings/stations",
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------
# The platform library, which had no reader at all
# --------------------------------------------------------------------------


async def a_library_station(
    db_session, title: str, *, exam_code: str = "sca", published: bool = True
) -> uuid.UUID:  # type: ignore[no-untyped-def]
    """A platform-owned station, written directly for speed.

    `POST /api/v1/platform/stations` now authors these properly and is covered
    in `test_platform_stations_routes.py`; this stays because the library tests
    below care about what is *in* the library, not how it got there.
    """
    from app.features.stations.models import Station, StationVersion

    exam = await ensure_exam(db_session, exam_code)
    assert exam is not None
    station = Station(
        owner_kind="platform",
        org_id=None,
        exam_id=exam.id,
        title=title,
        status="published" if published else "draft",
    )
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(
        station_id=station.id,
        org_id=None,
        version=1,
        content=CONTENT,
        status="published" if published else "draft",
    )
    db_session.add(version)
    await db_session.flush()
    station.current_version_id = version.id
    await db_session.flush()
    return station.id


async def test_the_library_lists_published_platform_stations(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("browser@example.com")
    await a_library_station(db_session, "Chest pain")
    await a_library_station(db_session, "Headache")

    response = await client.get("/api/v1/stations", headers=bearer(token))
    assert response.status_code == 200, response.text
    titles = {row["title"] for row in response.json()["items"]}
    assert {"Chest pain", "Headache"} <= titles


async def test_the_library_never_returns_station_content(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    """Browsing is not reading the answers.

    The content is the patient brief, the examiner's context and the marking
    guidance. A candidate may discover a station and bind its version; they may
    not read it before sitting it.
    """
    token = await make_actor("browser@example.com")
    await a_library_station(db_session, "Chest pain")

    row = (await client.get("/api/v1/stations", headers=bearer(token))).json()["items"][0]
    assert "content" not in row
    assert row["version_id"] is not None
    assert row["version"] == 1


async def test_the_library_excludes_drafts_and_org_stations(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    await make_station(client, admin)  # an org's own, published or not
    await a_library_station(db_session, "Still drafting", published=False)
    await a_library_station(db_session, "Ready")

    titles = {
        row["title"] for row in (await client.get("/api/v1/stations", headers=bearer(admin))).json()["items"]
    }
    assert "Ready" in titles
    assert "Still drafting" not in titles
    assert "Chest pain" not in titles


async def test_the_library_filters_by_exam(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("browser@example.com")
    await a_library_station(db_session, "A GP case", exam_code="sca")
    await a_library_station(db_session, "A psych case", exam_code="casc")

    body = (await client.get("/api/v1/stations?exam_code=casc", headers=bearer(token))).json()
    assert [row["title"] for row in body["items"]] == ["A psych case"]
    assert body["items"][0]["exam_code"] == "casc"


async def test_the_library_refuses_an_unknown_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Never defaulted: b2c fell back to `sca` and marked CASC with a GP rubric."""
    token = await make_actor("browser@example.com")
    response = await client.get("/api/v1/stations?exam_code=nonsense", headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_the_library_needs_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/stations")).status_code == 401


# --------------------------------------------------------------------------
# Deleting a draft, and the one thing a published version will accept
# --------------------------------------------------------------------------


async def test_a_draft_version_can_be_deleted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, admin)

    deleted = await client.delete(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1", headers=bearer(admin)
    )
    assert deleted.status_code == 204, deleted.text

    gone = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1",
        json={"content": CONTENT},
        headers=bearer(admin),
    )
    assert gone.status_code == 404
    assert gone.json()["code"] == "version_not_found"


async def test_a_published_version_cannot_be_deleted(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """It is what somebody's attempt was assessed against. Archive it instead."""
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, admin)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(admin)
    )

    response = await client.delete(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1", headers=bearer(admin)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_deletable"


async def test_the_reading_brief_is_correctable_on_a_published_version(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """T5, the documented exception to published content being immutable.

    The brief is what a candidate is handed before the station starts, so a
    typo in one must not require a new version and every circuit re-pointed.
    """
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, admin)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(admin)
    )

    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/brief",
        json={"reading_brief": "Mrs Patel, 42, chest pain for two days."},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["content"]["reading_brief"] == "Mrs Patel, 42, chest pain for two days."
    # The assessed content is untouched.
    assert response.json()["content"]["patient_information"] == CONTENT["patient_information"]
    assert response.json()["status"] == "published"


async def test_an_archived_version_accepts_nothing_at_all(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, admin)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(admin)
    )
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/archive", headers=bearer(admin)
    )

    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/brief",
        json={"reading_brief": "too late"},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "not_editable"
