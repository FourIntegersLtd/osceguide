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


async def a_browser(db_session, make_actor, email: str, *, exam_code: str = "sca") -> str:  # type: ignore[no-untyped-def]
    """Somebody who may browse one exam's library.

    The library is scoped to the exams a person may open, so a browser needs
    one. This uses the account's own exam rather than an entitlement, which is
    the trial case — the one that has to keep working, because somebody has to
    be able to see the library before they can buy anything in it.
    """
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor(email)
    await ensure_exam(db_session, exam_code)
    await db_session.execute(update(User).where(User.email == email).values(exam_code=exam_code))
    await db_session.flush()
    return token


async def member(make_actor, org_id: uuid.UUID, slug: str, role: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"{role}-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role=role),),
        active_org_slug=slug,
    )


async def make_station(
    client: AsyncClient, token: str, slug: str = "kings", content: dict | None = None
) -> dict:
    response = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": "Chest pain", "exam_code": "sca", "content": content or CONTENT},
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


async def test_a_draft_may_be_renamed(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    response = await client.patch(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1",
        json={"content": CONTENT, "title": "  Crushing chest pain "},
        headers=bearer(token),
    )
    assert response.status_code == 200
    listed = await client.get("/api/v1/orgs/kings/stations", headers=bearer(token))
    assert [s["title"] for s in listed.json()["items"]] == ["Crushing chest pain"]


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


async def test_an_org_station_search_matches_a_title_fragment(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """In SQL, not in the browser: a term must match the whole catalogue, not

    only the page a client happened to have already walked.
    """
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    for title in ("Chest pain", "Abdominal pain", "Headache"):
        response = await client.post(
            "/api/v1/orgs/kings/stations",
            json={"title": title, "exam_code": "sca", "content": CONTENT},
            headers=bearer(token),
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/orgs/kings/stations", params={"search": "pain"}, headers=bearer(token)
    )
    assert response.status_code == 200
    assert {s["title"] for s in response.json()["items"]} == {"Chest pain", "Abdominal pain"}


async def test_an_org_station_list_filters_by_exam_code(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The same exam scoping the library applies, answered server-side rather than by the browser
    walking every page and throwing rows away."""
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    root = await make_actor("root2-kings@osceguide.com", platform_admin=True)
    await create_exam(client, root, code="casc")
    await make_station(client, token)  # "Chest pain", exam_code sca
    await client.post(
        "/api/v1/orgs/kings/stations",
        json={"title": "Low mood", "exam_code": "casc", "content": CONTENT},
        headers=bearer(token),
    )

    response = await client.get(
        "/api/v1/orgs/kings/stations", params={"exam_code": "casc"}, headers=bearer(token)
    )
    assert response.status_code == 200, response.text
    assert [s["title"] for s in response.json()["items"]] == ["Low mood"]


async def test_an_org_station_list_excludes_archived_by_default(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    token = await member(make_actor, org_id, "kings", "owner")
    station = await make_station(client, token)
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/archive", headers=bearer(token)
    )

    default = await client.get("/api/v1/orgs/kings/stations", headers=bearer(token))
    assert default.json()["items"] == []

    included = await client.get(
        "/api/v1/orgs/kings/stations", params={"include_archived": "true"}, headers=bearer(token)
    )
    assert [s["title"] for s in included.json()["items"]] == ["Chest pain"]


async def test_a_trainee_may_browse_stations(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    await make_station(client, await member(make_actor, org_id, "kings", "owner"))
    response = await client.get(
        "/api/v1/orgs/kings/stations",
        headers=bearer(await member(make_actor, org_id, "kings", "trainee")),
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------
# The reader-scoped projection (S1): a trainee is handed a station document
# they may be examined on, so they get the candidate-facing half of it only.
# --------------------------------------------------------------------------

FULL_DOCUMENT = {
    "reading_brief": "Mrs Patel, 42, chest pain for two days.",
    "candidate_brief": "Older spelling of the same brief.",
    "clinical_scenario": "A GP consultation.",
    "doctor_information": {"doctor_task": "Take a history."},
    "patient_information": {
        "patient_biodata": "Mrs Patel, 42",
        "gender": "female",
        "persona": "anxious, guards the diagnosis",
        "expanded_history": "The hidden block.",
    },
    "patient_brief": "You are unwell and know why.",
    "management_plan": {"explanation": "The model answer."},
    "examiner_additional_info": ["Mark the ICE."],
}


async def listed_content(client: AsyncClient, token: str, slug: str = "kings") -> dict:
    response = await client.get(f"/api/v1/orgs/{slug}/stations", headers=bearer(token))
    assert response.status_code == 200, response.text
    [row] = response.json()["items"]
    return row["content"]


async def test_a_trainee_reader_gets_only_the_candidate_facing_document(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The leak this closes: `OrgReader` admits every rostered trainee, and the
    document is the patient's persona and the examiner's notes as much as it is
    the brief — for stations they are about to be examined on."""
    org_id = await seed_org(client, make_actor)
    await make_station(client, await member(make_actor, org_id, "kings", "owner"), content=FULL_DOCUMENT)
    trainee = await member(make_actor, org_id, "kings", "trainee")

    content = await listed_content(client, trainee)

    # The briefs and the candidate's own material survive, as on their
    # attempt's brief read.
    assert content["reading_brief"] == FULL_DOCUMENT["reading_brief"]
    assert content["candidate_brief"] == FULL_DOCUMENT["candidate_brief"]
    assert content["clinical_scenario"] == FULL_DOCUMENT["clinical_scenario"]
    assert content["doctor_information"] == FULL_DOCUMENT["doctor_information"]
    assert content["patient_information"] == {"patient_biodata": "Mrs Patel, 42", "gender": "female"}

    # The patient's half, the examiner's half and the model answer do not.
    for key in ("patient_brief", "management_plan", "examiner_additional_info"):
        assert key not in content
    assert "persona" not in content["patient_information"]
    assert "expanded_history" not in content["patient_information"]


async def test_a_practice_user_reads_as_a_trainee_does(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`practice_user` is the other end-user role `may_read_org` admits."""
    org_id = await seed_org(client, make_actor)
    await make_station(client, await member(make_actor, org_id, "kings", "owner"), content=FULL_DOCUMENT)

    content = await listed_content(client, await member(make_actor, org_id, "kings", "practice_user"))

    assert "patient_brief" not in content
    assert content["reading_brief"] == FULL_DOCUMENT["reading_brief"]


async def test_staff_and_admin_readers_get_the_whole_document(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Authoring, scheduling and marking all need the document complete: an
    org admin, an assigned supervisor, and a platform admin for support."""
    org_id = await seed_org(client, make_actor)
    owner = await member(make_actor, org_id, "kings", "owner")
    await make_station(client, owner, content=FULL_DOCUMENT)

    for token in (
        owner,
        await member(make_actor, org_id, "kings", "supervisor"),
        await make_actor("console@osceguide.com", platform_admin=True),
    ):
        assert await listed_content(client, token) == FULL_DOCUMENT


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
    token = await a_browser(db_session, make_actor, "browser@example.com")
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
    token = await a_browser(db_session, make_actor, "browser@example.com")
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
    # The library is scoped to the exams somebody may open, and an org's admin
    # is a person like any other here — their organisation's stations come from
    # the org routes, not this one.
    from sqlalchemy import update

    from app.features.identity.models import User

    await db_session.execute(
        update(User).where(User.email == "owner-kings@example.com").values(exam_code="sca")
    )
    await db_session.flush()

    titles = {
        row["title"] for row in (await client.get("/api/v1/stations", headers=bearer(admin))).json()["items"]
    }
    assert "Ready" in titles
    assert "Still drafting" not in titles
    assert "Chest pain" not in titles


async def test_the_library_filters_by_exam(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    token = await a_browser(db_session, make_actor, "browser@example.com", exam_code="casc")
    await a_library_station(db_session, "A GP case", exam_code="sca")
    await a_library_station(db_session, "A psych case", exam_code="casc")

    body = (await client.get("/api/v1/stations?exam_code=casc", headers=bearer(token))).json()
    assert [row["title"] for row in body["items"]] == ["A psych case"]
    assert body["items"][0]["exam_code"] == "casc"


async def test_the_library_refuses_an_unknown_exam(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Never defaulted: b2c fell back to `sca` and marked CASC with a GP rubric.

    A platform admin, because they are the one caller who may name any exam;
    for everybody else an exam they do not hold is refused before it is
    resolved, which is the test below.
    """
    token = await make_actor("browser@example.com", platform_admin=True)
    response = await client.get("/api/v1/stations?exam_code=nonsense", headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_the_library_is_scoped_to_the_exams_you_may_open(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """No exam named means yours, not everybody's.

    The retiring client had one exam per deployment and no picker at all. This
    route answered with every exam's stations at once, which is what put an
    "all exams" filter on a screen in a product where holding one exam is the
    norm — over a catalogue including exams nobody had bought.
    """
    token = await a_browser(db_session, make_actor, "gp@example.com", exam_code="sca")
    await a_library_station(db_session, "A GP case", exam_code="sca")
    await a_library_station(db_session, "A psych case", exam_code="casc")

    titles = {
        row["title"] for row in (await client.get("/api/v1/stations", headers=bearer(token))).json()["items"]
    }

    assert "A GP case" in titles
    assert "A psych case" not in titles


async def test_browsing_an_exam_you_do_not_hold_is_refused(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """Refused rather than answered empty: an empty list reads as "no stations yet"."""
    token = await a_browser(db_session, make_actor, "gp2@example.com", exam_code="sca")
    await ensure_exam(db_session, "casc")
    await a_library_station(db_session, "A psych case", exam_code="casc")

    response = await client.get("/api/v1/stations?exam_code=casc", headers=bearer(token))

    assert response.status_code == 403
    assert response.json()["code"] == "not_entitled"


async def test_a_platform_admin_browses_the_whole_catalogue(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    """Curating the library is their job, and they hold no entitlements at all."""
    token = await make_actor("staff@example.com", platform_admin=True)
    await a_library_station(db_session, "A GP case", exam_code="sca")
    await a_library_station(db_session, "A psych case", exam_code="casc")

    titles = {
        row["title"] for row in (await client.get("/api/v1/stations", headers=bearer(token))).json()["items"]
    }

    assert {"A GP case", "A psych case"} <= titles


async def test_somebody_with_no_exam_at_all_gets_an_empty_library(
    client: AsyncClient, make_actor, db_session
) -> None:
    """A brand-new account is not an error, it just has nothing yet."""
    token = await make_actor("blank@example.com")
    await a_library_station(db_session, "A GP case", exam_code="sca")

    response = await client.get("/api/v1/stations", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["items"] == []


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
    # Its only version was the draft, so the station went with it.
    assert gone.status_code == 404
    assert gone.json()["code"] == "station_not_found"


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


# --------------------------------------------------------------------------
# The whole document by audience, for the staff running a sitting
# --------------------------------------------------------------------------

SECTIONED = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "brief",
            "title": "Brief",
            "audience": "candidate",
            "blocks": [{"id": "task", "type": "longText", "label": "Task", "role": "candidate_brief"}],
        },
        {
            "id": "faculty",
            "title": "Faculty",
            "audience": "faculty",
            "blocks": [{"id": "debrief", "type": "list", "label": "Debrief", "role": "debrief"}],
        },
    ],
}


async def published_version(client: AsyncClient, token: str, station: dict) -> str:
    response = await client.post(
        f"/api/v1/orgs/kings/stations/{station['id']}/versions/1/publish", headers=bearer(token)
    )
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


async def test_a_supervisor_reads_every_audience_of_a_station(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    owner = await member(make_actor, org_id, "kings", "owner")
    template = await client.post(
        "/api/v1/orgs/kings/station-templates",
        json={"title": "Scenario", "exam_code": "sca", "structure": SECTIONED},
        headers=bearer(owner),
    )
    assert template.status_code == 201, template.text
    published = await client.post(
        f"/api/v1/orgs/kings/station-templates/{template.json()['id']}/publish", headers=bearer(owner)
    )
    assert published.status_code == 200, published.text
    created = await client.post(
        "/api/v1/orgs/kings/stations",
        json={
            "title": "Annual review",
            "exam_code": "sca",
            "content": {"task": "Review this patient.", "debrief": ["Ask how it felt."]},
            "template_version_id": template.json()["versions"][0]["id"],
        },
        headers=bearer(owner),
    )
    assert created.status_code == 201, created.text
    version_id = await published_version(client, owner, created.json())
    path = f"/api/v1/orgs/kings/station-versions/{version_id}/sections"

    read = await client.get(path, headers=bearer(await member(make_actor, org_id, "kings", "supervisor")))
    assert read.status_code == 200, read.text
    assert [
        (section["audience"], [block["id"] for block in section["blocks"]]) for section in read.json()
    ] == [
        ("candidate", ["task"]),
        ("faculty", ["debrief"]),
    ]

    trainee = await client.get(path, headers=bearer(await member(make_actor, org_id, "kings", "trainee")))
    assert trainee.status_code == 403, trainee.text


async def test_an_untemplated_station_has_no_sections_and_an_unknown_version_is_not_found(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id = await seed_org(client, make_actor)
    owner = await member(make_actor, org_id, "kings", "owner")
    version_id = await published_version(client, owner, await make_station(client, owner))

    read = await client.get(
        f"/api/v1/orgs/kings/station-versions/{version_id}/sections", headers=bearer(owner)
    )
    assert read.status_code == 200, read.text
    assert read.json() == []

    missing = await client.get(
        f"/api/v1/orgs/kings/station-versions/{uuid.uuid4()}/sections", headers=bearer(owner)
    )
    assert missing.status_code == 404, missing.text
