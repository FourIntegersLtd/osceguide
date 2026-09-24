"""Station images over HTTP: where they land, and taking one off again.

S3 is faked at its seam — these are about what the product does with a URL
once it has one, not about boto3.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.auth import Membership
from app.features.stations import service_photos
from tests.support.catalog import create_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

CONTENT: dict = {"doctor_information": {"task": "assess"}}


@pytest.fixture(autouse=True)
def fake_s3(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record what would have gone to the bucket, and what was removed."""
    deleted: list[str] = []

    def upload(settings, handle, key):  # type: ignore[no-untyped-def]
        return f"https://test-bucket.s3.eu-west-2.amazonaws.com/{key}"

    def delete(settings, url):  # type: ignore[no-untyped-def]
        deleted.append(url)

    monkeypatch.setattr(service_photos.storage, "put_object", upload)
    monkeypatch.setattr(service_photos.storage, "remove_object", delete)
    return deleted


async def seed_org(client: AsyncClient, make_actor, slug: str = "kings", exam: str = "sca"):  # type: ignore[no-untyped-def]
    token = await make_actor(f"root-{slug}-{exam}@osceguide.com", platform_admin=True)
    response = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    await create_exam(client, token, code=exam)
    return uuid.UUID(response.json()["id"])


async def admin_of(make_actor, org_id: uuid.UUID, slug: str) -> str:  # type: ignore[no-untyped-def]
    return await make_actor(
        f"author-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="admin"),),
        active_org_slug=slug,
    )


async def a_station(client: AsyncClient, token: str, exam: str, content: dict, slug: str = "kings") -> dict:
    response = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={"title": "Chest pain", "exam_code": exam, "content": content},
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def png(name: str = "xray.png", size: int = 2048) -> tuple[str, bytes, str]:
    return (name, b"\x89PNG" + b"0" * size, "image/png")


def photos_url(station: dict, slug: str = "kings") -> str:
    return f"/api/v1/orgs/{slug}/stations/{station['id']}/versions/{station['version']}/photos"


async def test_a_photo_lands_where_the_candidate_brief_reads_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`doctor_information.photos` is not a preference — it is the key the

    attempt runner's station brief already renders.
    """
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    station = await a_station(client, token, "sca", CONTENT)

    response = await client.post(photos_url(station), files={"files": png()}, headers=bearer(token))

    assert response.status_code == 200, response.text
    assert response.json()["uploaded"] == 1
    assert response.json()["failed"] == []
    photos = response.json()["version"]["content"]["doctor_information"]["photos"]
    assert len(photos) == 1
    assert photos[0].startswith("https://test-bucket.s3.eu-west-2.amazonaws.com/stations/")


async def test_an_ortho_clinical_stations_first_image_is_the_radiograph(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The ortho screens render the radiograph and the rest separately, so an

    image in the wrong field is an image nobody sees.
    """
    org = await seed_org(client, make_actor, slug="guys", exam="ortho")
    token = await admin_of(make_actor, org, "guys")
    station = await a_station(client, token, "ortho", {"station_type": "clinical"}, slug="guys")

    first = await client.post(
        photos_url(station, "guys"), files={"files": png("a.png")}, headers=bearer(token)
    )
    second = await client.post(
        photos_url(station, "guys"), files={"files": png("b.png")}, headers=bearer(token)
    )

    assert first.json()["version"]["content"]["radiograph_image_url"] is not None
    content = second.json()["version"]["content"]
    assert len(content["additional_image_urls"]) == 1
    assert content["radiograph_image_url"] != content["additional_image_urls"][0]


async def test_a_file_that_is_not_an_image_is_named_rather_than_losing_the_batch(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """One bad file must not throw away the good ones it arrived with."""
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    station = await a_station(client, token, "sca", CONTENT)

    response = await client.post(
        photos_url(station),
        files=[("files", png("good.png")), ("files", ("notes.pdf", b"%PDF-1.4", "application/pdf"))],
        headers=bearer(token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["uploaded"] == 1
    assert [f["filename"] for f in response.json()["failed"]] == ["notes.pdf"]
    assert len(response.json()["version"]["content"]["doctor_information"]["photos"]) == 1


async def test_removing_a_photo_takes_it_out_of_the_bucket_too(
    client: AsyncClient, make_actor, fake_s3: list[str]
) -> None:  # type: ignore[no-untyped-def]
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    station = await a_station(client, token, "sca", CONTENT)
    uploaded = await client.post(photos_url(station), files={"files": png()}, headers=bearer(token))
    url = uploaded.json()["version"]["content"]["doctor_information"]["photos"][0]

    response = await client.post(
        f"{photos_url(station)}/remove", json={"photo_url": url}, headers=bearer(token)
    )

    assert response.status_code == 200, response.text
    assert response.json()["content"]["doctor_information"]["photos"] == []
    assert fake_s3 == [url]


async def test_a_photo_that_is_not_on_this_station_is_refused(
    client: AsyncClient, make_actor, fake_s3: list[str]
) -> None:  # type: ignore[no-untyped-def]
    """The retiring route deleted whatever URL it was handed, so any authorised

    caller could destroy any object in the bucket by naming it.
    """
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    station = await a_station(client, token, "sca", CONTENT)

    response = await client.post(
        f"{photos_url(station)}/remove",
        json={"photo_url": "https://test-bucket.s3.eu-west-2.amazonaws.com/stations/elsewhere.png"},
        headers=bearer(token),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "photo_not_on_station"
    assert fake_s3 == []


async def test_a_trainee_may_not_put_images_on_a_station(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org = await seed_org(client, make_actor)
    author = await admin_of(make_actor, org, "kings")
    station = await a_station(client, author, "sca", CONTENT)
    trainee = await make_actor(
        "trainee-kings@example.com",
        memberships=(Membership(org_id=org, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )

    response = await client.post(photos_url(station), files={"files": png()}, headers=bearer(trainee))

    assert response.status_code == 403
