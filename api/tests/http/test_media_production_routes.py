"""Media production enqueue routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _summary(client: AsyncClient, admin: str) -> dict:
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": "AV Summary Test", "content": {"red_flags": ["x"]}},
        headers=bearer(admin),
    )
    assert response.status_code == 201
    return response.json()


async def test_generate_podcast_wrong_kind(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-wrong@osceguide.com", platform_admin=True)
    blog = await client.post(
        "/api/v1/media",
        json={"kind": "blog", "title": "Blog", "content": {"body_md": "hi"}},
        headers=bearer(admin),
    )
    item_id = blog.json()["id"]
    response = await client.post(
        f"/api/v1/media/{item_id}/generate-podcast",
        headers=bearer(admin),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "media_wrong_kind"


async def test_enqueue_summary_podcast_sets_status(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-pod@osceguide.com", platform_admin=True)
    item = await _summary(client, admin)
    response = await client.post(
        f"/api/v1/media/{item['id']}/generate-podcast",
        headers=bearer(admin),
    )
    assert response.status_code == 202
    body = response.json()
    assert body["content"]["status"] == "generating_podcast"


async def test_a_failed_render_still_tells_the_requester(
    client: AsyncClient, make_actor, db_session, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """`media.updated` must fire whichever way the render ends, or `MediaDetailScreen`

    would sit on its "in progress" banner forever after a model failure. The render
    itself is stubbed to raise, since nothing here should call out to a real TTS
    service; that failure is exactly the case where the job's own status write and
    its publish used to be lost together, as both lived inside a transaction the
    exception rolled back.
    """
    import uuid

    from app.core.events import PENDING_KEY, user_topic
    from app.features.identity import repository as identity_repository
    from app.features.media_production import podcast_tts
    from app.features.media_production.service import MEDIA_UPDATED, run_summary_podcast_job

    email = "av-fail@osceguide.com"
    admin = await make_actor(email, platform_admin=True)
    item = await _summary(client, admin)
    media_id = uuid.UUID(item["id"])
    user = await identity_repository.user_by_email(db_session, email)
    assert user is not None

    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("no TTS in tests")

    monkeypatch.setattr(podcast_tts, "produce_summary_podcast", _boom)

    # The job records the failure on the item rather than raising, so the failed
    # status and this publish land in the same transaction instead of both being
    # rolled back by an exception the job queue would otherwise have to retry.
    await run_summary_podcast_job(db_session, media_id, requested_by=user.id)

    assert (
        user_topic(user.id),
        MEDIA_UPDATED,
        {"media_id": str(media_id)},
    ) in db_session.info[PENDING_KEY]


async def test_enqueue_twice_conflicts(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-twice@osceguide.com", platform_admin=True)
    item = await _summary(client, admin)
    url = f"/api/v1/media/{item['id']}/generate-podcast"
    await client.post(url, headers=bearer(admin))
    again = await client.post(url, headers=bearer(admin))
    assert again.status_code == 409
    assert again.json()["code"] == "av_already_running"
