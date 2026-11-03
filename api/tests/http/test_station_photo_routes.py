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

# A b2c-shaped station: its photos sit inside the doctor's information, which
# the template's `doctor_photos` block reads with the section prefix dropped.
CONTENT: dict = {"doctor_information": {"task": "assess", "photos": []}}

TEMPLATE: dict = {
    "sections": [
        {
            "id": "doctor_information",
            "title": "Doctor information",
            "audience": "candidate",
            "blocks": [
                {"id": "doctor_task", "type": "longText", "role": "candidate_brief", "label": "Task"},
                {"id": "doctor_photos", "type": "media", "role": "candidate_brief", "label": "Photos"},
            ],
        },
        {
            "id": "imaging",
            "title": "Imaging",
            "audience": "candidate",
            "blocks": [
                {"id": "radiograph", "type": "media", "role": "candidate_brief", "label": "Radiograph"}
            ],
        },
    ]
}


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


async def a_template(client: AsyncClient, token: str, exam: str, slug: str) -> str:
    """A published org template with two media blocks; returns its version id."""
    created = await client.post(
        f"/api/v1/orgs/{slug}/station-templates",
        json={"title": "Consultation", "exam_code": exam, "structure": TEMPLATE},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    published = await client.post(
        f"/api/v1/orgs/{slug}/station-templates/{created.json()['id']}/publish", headers=bearer(token)
    )
    assert published.status_code == 200, published.text
    return str(published.json()["id"])


async def a_station(client: AsyncClient, token: str, exam: str, content: dict, slug: str = "kings") -> dict:
    template_version_id = await a_template(client, token, exam, slug)
    response = await client.post(
        f"/api/v1/orgs/{slug}/stations",
        json={
            "title": "Chest pain",
            "exam_code": exam,
            "content": content,
            "template_version_id": template_version_id,
        },
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def png(name: str = "xray.png", size: int = 2048) -> tuple[str, bytes, str]:
    return (name, b"\x89PNG\r\n\x1a\n" + b"0" * size, "image/png")


def photos_url(station: dict, slug: str = "kings", block: str = "doctor_photos") -> str:
    base = f"/api/v1/orgs/{slug}/stations/{station['id']}/versions/{station['version']}/photos"
    return f"{base}?block={block}"


def remove_url(station: dict, slug: str = "kings") -> str:
    return f"/api/v1/orgs/{slug}/stations/{station['id']}/versions/{station['version']}/photos/remove"


async def test_a_photo_lands_where_its_media_block_reads_it(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`doctor_photos` reads a b2c station's `doctor_information.photos`, so that is where it goes."""
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


async def test_a_b2c_section_without_photos_takes_them_under_the_block_id(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    station = await a_station(client, token, "sca", {"doctor_information": {"task": "assess"}})

    response = await client.post(photos_url(station), files={"files": png()}, headers=bearer(token))

    assert response.status_code == 200, response.text
    doctor = response.json()["version"]["content"]["doctor_information"]
    assert len(doctor["doctor_photos"]) == 1
    assert "photos" not in doctor


async def test_a_block_with_no_stored_value_is_written_flat_under_its_id(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org = await seed_org(client, make_actor, slug="guys", exam="ortho")
    token = await admin_of(make_actor, org, "guys")
    station = await a_station(client, token, "ortho", {}, slug="guys")

    first = await client.post(
        photos_url(station, "guys", "radiograph"), files={"files": png("a.png")}, headers=bearer(token)
    )
    second = await client.post(
        photos_url(station, "guys", "radiograph"), files={"files": png("b.png")}, headers=bearer(token)
    )

    assert first.status_code == 200, first.text
    radiographs = second.json()["version"]["content"]["radiograph"]
    assert len(radiographs) == 2
    assert radiographs[0] == first.json()["version"]["content"]["radiograph"][0]


async def test_a_block_that_does_not_take_images_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org = await seed_org(client, make_actor)
    token = await admin_of(make_actor, org, "kings")
    station = await a_station(client, token, "sca", CONTENT)

    response = await client.post(
        photos_url(station, block="doctor_task"), files={"files": png()}, headers=bearer(token)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "not_a_media_block"


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

    response = await client.post(remove_url(station), json={"photo_url": url}, headers=bearer(token))

    assert response.status_code == 200, response.text
    assert response.json()["content"]["doctor_information"]["photos"] == []
    assert "X-Amz-Signature=" in url  # the author was shown a signed link and sent it back
    assert fake_s3 == [url.split("?")[0]]  # the object deleted is the plain stored one


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
        remove_url(station),
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
