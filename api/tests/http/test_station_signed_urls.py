"""A station's photo links are signed on every read that returns them, and only for that station.

Station content is written by org authors, so a link in it proves nothing: a read may sign a file
only from the folder its own station uploads to. The same rule is asserted on each way a link reaches
a screen: the author's version, the version history, the staff sections, and a candidate's brief and
review.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assistant import service as assistant_service
from app.features.attempts import domain
from app.features.attempts import repository as attempts_repo
from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from app.features.media_production import service_storage
from app.features.stations import repository as stations_repo
from app.features.stations import service as stations_service
from tests.http.test_attempt_material_routes import NOW, STATION_CONTENT, _station
from tests.http.test_station_photo_routes import CONTENT, a_station, admin_of, seed_org
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

ORIGIN = "https://osceguide.s3.eu-west-2.amazonaws.com"
PODCAST = f"{ORIGIN}/podcasts/sca/episodes/0b5f1c4e.mp3"


@pytest.fixture(autouse=True)
def bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        aws_s3_bucket="osceguide",
        aws_region="eu-west-2",
        aws_access_key_id="AKIAFAKE",
        aws_secret_access_key="fake",  # noqa: S106
    )
    monkeypatch.setattr(service_storage, "get_settings", lambda: settings)


def photo_links(station_id: str, other_station_id: str) -> tuple[str, str]:
    """This station's own photo, and a photo in another station's folder."""
    return f"{ORIGIN}/stations/{station_id}/own.png", f"{ORIGIN}/stations/{other_station_id}/theirs.png"


def assert_only_own_is_signed(photos: list[str], own: str, theirs: str) -> None:
    assert photos[0].startswith(own + "?") and "X-Amz-Signature=" in photos[0]
    assert photos[1:] == [theirs, PODCAST]  # another folder's file, and a podcast: never signed here


async def stations_with_links(client: AsyncClient, make_actor) -> tuple[str, dict, str, str]:  # type: ignore[no-untyped-def]
    """Two stations in one org, the first with a photo of its own and links to files it does not own."""
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    mine = await a_station(client, token, "sca", CONTENT)
    other = await a_station(client, token, "sca", CONTENT)
    own, theirs = photo_links(mine["id"], other["id"])
    edited = await client.patch(
        f"/api/v1/orgs/kings/stations/{mine['id']}/versions/{mine['version']}",
        json={"content": {"doctor_information": {"task": "assess", "photos": [own, theirs, PODCAST]}}},
        headers=bearer(token),
    )
    assert edited.status_code == 200, edited.text
    return token, mine, own, theirs


async def test_an_author_reads_back_a_signed_photo_of_their_own_station_only(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, mine, own, theirs = await stations_with_links(client, make_actor)

    listing = await client.get("/api/v1/orgs/kings/stations?limit=50", headers=bearer(token))
    shown = next(item for item in listing.json()["items"] if item["id"] == mine["id"])

    assert_only_own_is_signed(shown["content"]["doctor_information"]["photos"], own, theirs)


async def test_the_version_history_signs_the_same_way(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token, mine, own, theirs = await stations_with_links(client, make_actor)

    history = await client.get(f"/api/v1/stations/{mine['id']}/versions", headers=bearer(token))

    assert history.status_code == 200, history.text
    assert_only_own_is_signed(history.json()[0]["content"]["doctor_information"]["photos"], own, theirs)


async def test_the_staff_sections_sign_the_same_way(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token, mine, own, theirs = await stations_with_links(client, make_actor)
    version_id = (await client.get(f"/api/v1/stations/{mine['id']}/versions", headers=bearer(token))).json()[
        0
    ]["id"]

    response = await client.get(
        f"/api/v1/orgs/kings/station-versions/{version_id}/sections", headers=bearer(token)
    )

    assert response.status_code == 200, response.text
    photos = next(
        block["value"]
        for section in response.json()
        for block in section["blocks"]
        if block["id"] == "doctor_photos"
    )
    assert_only_own_is_signed(photos, own, theirs)


async def test_a_stranger_and_an_anonymous_caller_get_no_link(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token, mine, *_ = await stations_with_links(client, make_actor)
    rival_org = await seed_org(client, make_actor, slug="rival")
    rival = await admin_of(make_actor, rival_org, "rival")
    paths = (
        f"/api/v1/stations/{mine['id']}/versions",
        "/api/v1/orgs/kings/stations?limit=50",
    )

    for path in paths:
        anonymous = await client.get(path)
        stranger = await client.get(path, headers=bearer(rival))
        assert anonymous.status_code == 401, path
        assert stranger.status_code in (403, 404), path
        assert "amazonaws" not in anonymous.text + stranger.text


async def candidate_attempt(db_session: AsyncSession, email: str) -> tuple[uuid.UUID, str, str]:
    """An entitled candidate's attempt on a library station whose brief holds three photo links."""
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await ent_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    station_id, version_id = await _station(db_session, exam.id)
    own, theirs = photo_links(str(station_id), str(uuid.uuid4()))
    content = {**STATION_CONTENT, "doctor_information": {**STATION_CONTENT["doctor_information"]}}
    content["doctor_information"]["photos"] = [own, theirs, PODCAST]
    await stations_repo.set_version_content(db_session, None, version_id, content=content)
    attempt = await attempts_repo.create_attempt(
        db_session,
        kind="practice",
        user_id=user.id,
        exam_id=exam.id,
        org_id=None,
        station_version_id=version_id,
    )
    await attempts_repo.set_status(db_session, attempt.id, status=domain.Status.RUNNING, at=NOW)
    await attempts_repo.set_status(db_session, attempt.id, status=domain.Status.INTERACTION_COMPLETE, at=NOW)
    attempt_id = attempt.id
    await db_session.commit()
    return attempt_id, own, theirs


@pytest.mark.parametrize("read", ["brief", "review"])
async def test_a_candidates_brief_and_review_sign_the_stations_photo(
    client: AsyncClient, db_session: AsyncSession, make_actor, read: str
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor(f"{read}-signed@example.com")
    attempt_id, own, theirs = await candidate_attempt(db_session, f"{read}-signed@example.com")

    response = await client.get(f"/api/v1/attempts/{attempt_id}/{read}", headers=bearer(token))

    assert response.status_code == 200, response.text
    section = next(item for item in response.json()["sections"] if item["id"] == "doctor_information")
    photos = next(block["value"] for block in section["blocks"] if block["id"] == "photos")
    assert_only_own_is_signed(photos, own, theirs)


@pytest.mark.parametrize("read", ["brief", "review"])
async def test_nobody_else_gets_a_link_from_a_brief_or_review(
    client: AsyncClient, db_session: AsyncSession, make_actor, read: str
) -> None:  # type: ignore[no-untyped-def]
    await make_actor(f"{read}-owner@example.com")
    attempt_id, *_ = await candidate_attempt(db_session, f"{read}-owner@example.com")
    intruder = await make_actor(f"{read}-intruder@example.com")

    anonymous = await client.get(f"/api/v1/attempts/{attempt_id}/{read}")
    stranger = await client.get(f"/api/v1/attempts/{attempt_id}/{read}", headers=bearer(intruder))

    assert (anonymous.status_code, stranger.status_code) == (401, 403)
    assert "amazonaws" not in anonymous.text + stranger.text


async def stored_content(db_session: AsyncSession, station_id: str) -> dict:
    """The version row as the database holds it, bypassing every read."""
    row = await db_session.execute(
        text("select content from station_versions where station_id = :id order by version desc limit 1"),
        {"id": station_id},
    )
    return row.scalar_one()


async def test_saving_back_what_an_author_was_shown_stores_plain_links(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token, mine, own, theirs = await stations_with_links(client, make_actor)
    shown = (await client.get(f"/api/v1/stations/{mine['id']}/versions", headers=bearer(token))).json()[0]
    assert "X-Amz-Signature=" in shown["content"]["doctor_information"]["photos"][0]

    saved = await client.patch(
        f"/api/v1/orgs/kings/stations/{mine['id']}/versions/{mine['version']}",
        json={"content": shown["content"]},
        headers=bearer(token),
    )

    assert saved.status_code == 200, saved.text
    assert (await stored_content(db_session, mine["id"]))["doctor_information"]["photos"] == [
        own,
        theirs,
        PODCAST,
    ]


async def test_a_station_created_from_signed_links_stores_plain_links(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token, mine, own, theirs = await stations_with_links(client, make_actor)
    shown = (await client.get(f"/api/v1/stations/{mine['id']}/versions", headers=bearer(token))).json()[0]

    copy = await a_station(client, token, "sca", shown["content"])

    stored_photos = (await stored_content(db_session, copy["id"]))["doctor_information"]["photos"]
    assert stored_photos == [own, theirs, PODCAST]


async def library_version_with_links(db_session: AsyncSession) -> tuple[uuid.UUID, str, str]:
    """A published library station whose flat brief and prompt-facing content carry file links."""
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station_id, version_id = await _station(db_session, exam.id)
    own, theirs = photo_links(str(station_id), str(uuid.uuid4()))
    content = {
        "reading_brief": f"Examine the film ![x-ray]({own}) and ![other]({theirs}) then advise.",
        "doctor_information": {"task_instructions": "Take a history.", "photos": [own, theirs]},
    }
    await stations_repo.set_version_content(db_session, None, version_id, content=content)
    await db_session.commit()
    return version_id, own, theirs


async def test_a_flat_reading_brief_signs_this_stations_own_links_only(db_session: AsyncSession) -> None:
    version_id, own, theirs = await library_version_with_links(db_session)

    brief = await stations_service.reading_brief(db_session, None, version_id)

    assert brief is not None and brief.text is not None
    assert f"![x-ray]({own}?X-Amz-Algorithm=" in brief.text
    assert f"![other]({theirs})" in brief.text
    assert brief.text.endswith(" then advise.")


async def test_the_assistant_prompt_carries_the_words_but_no_file_links(db_session: AsyncSession) -> None:
    version_id, *_ = await library_version_with_links(db_session)

    context = await assistant_service._station_context_from_db(
        db_session, org_id=None, station_version_id=version_id
    )

    assert context is not None
    flattened = json.dumps(context)
    assert "amazonaws" not in flattened and "X-Amz" not in flattened
    assert "Take a history." in flattened and "then advise." in flattened
