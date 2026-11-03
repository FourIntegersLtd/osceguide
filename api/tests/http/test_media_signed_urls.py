"""A paid file's link is signed for the reader entitled to it and absent for everyone else."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.features.media_production import service_storage
from tests.http.test_media_routes import index  # noqa: F401
from tests.support.catalog import create_exam, ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

ORIGIN = "https://osceguide.s3.eu-west-2.amazonaws.com"
DECK = f"{ORIGIN}/teaching_videos/sca/a_topic_0b5f1c4e-9d3a-4c7e-8a55-3f1d2e6b7a90.mp4"
PODCAST = f"{ORIGIN}/podcasts/sca/episodes/0b5f1c4e.mp3"
PICTURE = f"{ORIGIN}/teaching_videos/sca/pictures/aspirin.jpg"
MARKETING = f"{ORIGIN}/marketing/osceguide-sca.mp4"
STATION_PHOTO = f"{ORIGIN}/stations/0b5f1c4e-9d3a-4c7e-8a55-3f1d2e6b7a90/own.png"
CONTENT = {
    "station_photo": STATION_PHOTO,
    "final_video_url": DECK,
    "podcast_url": PODCAST,
    "slides": [{"image_urls": [PICTURE, DECK]}],
    "hero": MARKETING,
}


@pytest.fixture(autouse=True)
def bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        aws_s3_bucket="osceguide",
        aws_region="eu-west-2",
        aws_access_key_id="AKIAFAKE",
        aws_secret_access_key="fake",
    )
    monkeypatch.setattr(service_storage, "get_settings", lambda: settings)


async def published_deck(client: AsyncClient, admin: str) -> dict:
    created = await client.post(
        "/api/v1/media",
        json={"kind": "slide_deck", "title": "Signed Deck", "content": CONTENT, "exam_code": "sca"},
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text
    published = await client.post(f"/api/v1/media/{created.json()['id']}/publish", headers=bearer(admin))
    assert published.status_code == 200, published.text
    return created.json()


async def test_entitled_reader_gets_signed_links_and_locked_readers_get_none(
    client: AsyncClient,
    make_actor,
    db_session,
    index,  # noqa: F811
) -> None:  # type: ignore[no-untyped-def]
    from app.features.entitlements import repository as ent_repo
    from app.features.identity import repository as identity_repo

    admin = await make_actor("sg-admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    deck = await published_deck(client, admin)
    paid = await make_actor("sg-paid@example.com")
    user = await identity_repo.user_by_email(db_session, "sg-paid@example.com")
    exam = await ensure_exam(db_session, "sca")
    await ent_repo.grant(
        session=db_session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await db_session.commit()
    expired = await make_actor("sg-expired@example.com", exam_code="sca")
    await db_session.execute(
        text(
            "update users set created_at = now() - interval '40 days' where email = 'sg-expired@example.com'"
        )
    )
    await db_session.commit()

    entitled = (await client.get(f"/api/v1/media/{deck['slug']}", headers=bearer(paid))).json()["content"]

    assert "X-Amz-Signature=" in entitled["final_video_url"] and entitled["final_video_url"].startswith(DECK)
    assert "X-Amz-Signature=" in entitled["podcast_url"]
    assert entitled["slides"][0]["image_urls"][0].startswith(PICTURE + "?")  # pictures are signed too
    assert entitled["slides"][0]["image_urls"][1].startswith(DECK + "?")
    assert entitled["hero"] == MARKETING
    assert entitled["station_photo"] == STATION_PHOTO  # not study media: never signed here
    for headers in ({}, bearer(expired)):
        listing = await client.get("/api/v1/media?limit=50", headers=headers)
        single = await client.get(f"/api/v1/media/{deck['slug']}", headers=headers)
        assert "amazonaws" not in listing.text + single.text


async def test_staff_see_signed_links_but_the_row_keeps_the_plain_ones(
    client: AsyncClient,
    make_actor,
    db_session,
    index,  # noqa: F811
) -> None:  # type: ignore[no-untyped-def]

    admin = await make_actor("sg-staff@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    created = await client.post(
        "/api/v1/media",
        json={"kind": "slide_deck", "title": "Staff Deck", "content": CONTENT, "exam_code": "sca"},
        headers=bearer(admin),
    )
    shown = created.json()["content"]
    assert "X-Amz-Signature=" in shown["final_video_url"]

    # The staff form saves back what it was shown; the stored link must not become an expiring one.
    patched = await client.patch(
        f"/api/v1/media/{created.json()['id']}", json={"content": shown}, headers=bearer(admin)
    )
    assert patched.status_code == 200, patched.text
    stored = await db_session.execute(text("select content from media_items where title = 'Staff Deck'"))
    assert stored.scalar_one()["final_video_url"] == DECK
