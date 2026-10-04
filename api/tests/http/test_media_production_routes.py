"""Media production enqueue routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.support.tokens import bearer

pytestmark = pytest.mark.db


SCRIPT = "Ben: Chest pain on exertion needs an ECG.\n\nMichelle: And a same-day review."
LINES = ["Ben: Chest pain on exertion needs an ECG.", "Michelle: And a same-day review."]


async def _summary(client: AsyncClient, admin: str, *, checked: bool = True) -> dict:
    """A summary with its podcast script written; `checked` says whether that script has been read."""
    content: dict = {"red_flags": ["x"], "script": SCRIPT}
    if checked:
        content["review"] = {"script": {"lines": LINES}}
    response = await client.post(
        "/api/v1/media",
        json={"kind": "summary", "title": "AV Summary Test", "content": content},
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


async def test_voicing_is_refused_until_the_script_has_been_checked(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-unchecked@osceguide.com", platform_admin=True)
    item = await _summary(client, admin, checked=False)

    response = await client.post(f"/api/v1/media/{item['id']}/generate-podcast", headers=bearer(admin))

    assert response.status_code == 409
    assert response.json()["code"] == "script_not_checked"


async def test_voicing_is_refused_again_once_a_checked_script_is_edited(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("av-edited@osceguide.com", platform_admin=True)
    item = await _summary(client, admin)
    edited = {**item["content"], "script": SCRIPT.replace("an ECG", "a troponin")}
    saved = await client.patch(f"/api/v1/media/{item['id']}", json={"content": edited}, headers=bearer(admin))
    assert saved.status_code == 200

    response = await client.post(f"/api/v1/media/{item['id']}/generate-podcast", headers=bearer(admin))

    assert response.status_code == 409
    assert response.json()["code"] == "script_not_checked"


@pytest.mark.parametrize("route", ["check-facts", "write-script"])
async def test_a_check_is_refused_for_material_that_is_never_spoken(
    client: AsyncClient, make_actor, route: str
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor(f"av-blog-{route}@osceguide.com", platform_admin=True)
    blog = await client.post(
        "/api/v1/media",
        json={"kind": "blog", "title": "Blog", "content": {"body_md": "hi"}},
        headers=bearer(admin),
    )

    response = await client.post(f"/api/v1/media/{blog.json()['id']}/{route}", json={}, headers=bearer(admin))

    assert response.status_code == 422
    assert response.json()["code"] == "media_wrong_kind"


@pytest.mark.parametrize(
    ("route", "status"), [("check-facts", "checking_facts"), ("write-script", "writing_script")]
)
async def test_a_check_is_queued_once_and_shows_as_running(
    client: AsyncClient, make_actor, route: str, status: str
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor(f"av-queue-{route}@osceguide.com", platform_admin=True)
    item = await _summary(client, admin, checked=False)
    url = f"/api/v1/media/{item['id']}/{route}"

    first = await client.post(url, json={}, headers=bearer(admin))
    again = await client.post(url, json={}, headers=bearer(admin))

    assert first.status_code == 202
    assert first.json()["content"]["status"] == status
    assert again.status_code == 409
    assert again.json()["code"] == "av_already_running"


async def test_a_learner_is_never_sent_checks_only_staff(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Sources and what was flagged are for the people editing: the published item carries neither."""
    admin = await make_actor("av-review-read@osceguide.com", platform_admin=True)
    item = await _summary(client, admin)
    assert item["content"]["review"] == {"script": {"lines": LINES}}
    published = await client.post(f"/api/v1/media/{item['id']}/publish", headers=bearer(admin))
    assert published.status_code == 200

    as_staff = await client.get(f"/api/v1/media/by-id/{item['id']}", headers=bearer(admin))
    as_learner = await client.get(f"/api/v1/media/{item['slug']}")

    assert as_staff.json()["content"]["review"] == {"script": {"lines": LINES}}
    assert as_learner.status_code == 200
    assert as_learner.json()["content"]["script"] == SCRIPT
    assert "review" not in as_learner.json()["content"]


async def test_writing_a_script_checks_it_and_then_voicing_is_allowed(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    import uuid

    from app.features.identity import repository as identity_repository
    from app.features.media_production.service import run_script_write_job

    email = "av-write@osceguide.com"
    admin = await make_actor(email, platform_admin=True)
    item = await _summary(client, admin, checked=False)
    user = await identity_repository.user_by_email(db_session, email)
    assert user is not None
    user_id = user.id

    await run_script_write_job(
        db_session,
        uuid.UUID(item["id"]),
        requested_by=user_id,
        rewrite=False,
        complete=lambda prompt: '{"issues": []}',
    )

    written = (await client.get(f"/api/v1/media/by-id/{item['id']}", headers=bearer(admin))).json()["content"]
    assert written["status"] == "awaiting_review"
    assert written["script"] == SCRIPT
    assert written["review"]["script"]["lines"] == LINES
    assert written["review"]["script"]["issues"] == []
    voiced = await client.post(f"/api/v1/media/{item['id']}/generate-podcast", headers=bearer(admin))
    assert voiced.status_code == 202


async def test_a_fact_check_stores_its_verdicts_and_puts_the_status_back(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    import json
    import uuid

    from app.core.ports import GuidelinePassage
    from app.features.identity import repository as identity_repository
    from app.features.media_production.service import run_fact_check_job, save_fact_progress
    from tests.support.fakes import FakeGuidelineIndex, FakeGuidelineWeb

    email = "av-facts@osceguide.com"
    admin = await make_actor(email, platform_admin=True)
    item = await _summary(client, admin)
    user = await identity_repository.user_by_email(db_session, email)
    assert user is not None
    user_id = user.id
    queued = await client.post(f"/api/v1/media/{item['id']}/check-facts", headers=bearer(admin))
    assert queued.json()["content"]["status"] == "checking_facts"

    def model(prompt: str) -> str:
        if "List the clinical claims" in prompt:
            return json.dumps(
                {"claims": [{"section": 1, "claim": "Exertional chest pain needs an ECG", "question": "q"}]}
            )
        return json.dumps({"verdict": "supported", "evidence": 1, "quote": "12-lead ECG", "why": "Same."})

    web = FakeGuidelineWeb(None)
    seen_while_running: list[tuple[str, dict[str, int], int]] = []

    async def progress(facts: dict[str, object]) -> None:
        await save_fact_progress(db_session, uuid.UUID(item["id"]), requested_by=user_id, facts=facts)
        read = (await client.get(f"/api/v1/media/by-id/{item['id']}", headers=bearer(admin))).json()[
            "content"
        ]
        running = read["review"]["facts"]
        seen_while_running.append((read["status"], running["progress"], len(running["claims"])))

    await run_fact_check_job(
        db_session,
        uuid.UUID(item["id"]),
        requested_by=user_id,
        previous_status=None,
        progress=progress,
        guidelines=FakeGuidelineIndex(
            [GuidelinePassage(source="NICE CG95", text="Take a 12-lead ECG.", score=0.9)]
        ),
        web=web,
        complete=model,
    )

    checked = (await client.get(f"/api/v1/media/by-id/{item['id']}", headers=bearer(admin))).json()["content"]
    assert "status" not in checked
    assert [(claim["claim"], claim["verdict"]) for claim in checked["review"]["facts"]["claims"]] == [
        ("Exertional chest pain needs an ECG", "supported")
    ]
    assert checked["review"]["script"] == {"lines": LINES}
    assert checked["script"] == SCRIPT
    assert web.questions == ["q"]
    assert seen_while_running == [
        ("checking_facts", {"done": 0, "total": 1}, 0),
        ("checking_facts", {"done": 1, "total": 1}, 1),
    ]
