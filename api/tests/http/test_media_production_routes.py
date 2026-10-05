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


BRIEF = {"brief": "Teach HRT in the menopause.", "source_text": "Mrs A, 52, hot flushes."}
PRODUCED = {"topic": "Menopause", "slides": [{"title": "HRT", "bullets": ["Offer HRT."]}]}


async def _deck(client: AsyncClient, admin: str) -> str:
    """An empty slide deck draft, by id."""
    response = await client.post(
        "/api/v1/media",
        json={"kind": "slide_deck", "title": "Menopause", "content": {}},
        headers=bearer(admin),
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _produce_job(db_session, email: str, answers: dict):  # type: ignore[no-untyped-def]
    """The produce job with a scripted model and generator, saving through the test's own session."""
    import uuid

    from app.features.identity import repository as identity_repository
    from app.features.media_production.service_produce import run_produce_job
    from tests.support.produce_kit import answering, one_session, produce_kit

    turn, _ = answering(answers, tokens=100)
    kit, _ = produce_kit(PRODUCED)

    async def job(item: dict) -> None:
        user = await identity_repository.user_by_email(db_session, email)
        await run_produce_job(
            uuid.UUID(item["id"]),
            requested_by=user.id,
            run_id=item["content"]["review"]["run"]["id"],
            sessions=one_session(db_session),
            turn=turn,
            kit=kit,
        )

    return job


async def test_producing_drafts_the_item_logs_each_step_and_tells_the_requester(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    from app.core.events import PENDING_KEY

    admin = await make_actor("produce@example.com", platform_admin=True)
    item_id = await _deck(client, admin)

    started = await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))

    assert started.status_code == 202
    assert started.json()["content"]["status"] == "producing"
    assert started.json()["content"]["review"]["brief"] == BRIEF

    # The model is asked only to choose the picture and pick it from a search; code does the rest.
    answers = {"choose": [{"slides": [{"slide": 1, "search": "estradiol patch"}]}], "pick": [{"picture": 1}]}
    job = _produce_job(db_session, "produce@example.com", answers)
    await job(started.json())
    assert ("media.updated", {"media_id": item_id}) in [event[1:] for event in db_session.info[PENDING_KEY]]

    content = (await client.get(f"/api/v1/media/by-id/{item_id}", headers=bearer(admin))).json()["content"]
    run = content["review"]["run"]
    assert content["slides"][0]["bullets"] == PRODUCED["slides"][0]["bullets"]
    assert content["status"] == "awaiting_review"
    steps = [step["tool"] for step in run["steps"]]
    assert steps.count("check_facts") == 1
    assert steps == ["write_draft", "choose_pictures", "set_picture", "check_facts", "write_script", "finish"]
    assert (run["outcome"], run["tokens"], run["open"]) == ("finished", 200, [])
    assert run["summary"].startswith("Drafted the slide deck 'Menopause' in 1 slides, 1 with a picture.")


async def test_produce_is_refused_for_a_blog_and_while_the_item_is_being_worked_on(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("produce-refused@example.com", platform_admin=True)
    blog = await client.post(
        "/api/v1/media",
        json={"kind": "blog", "title": "Blog", "content": {"body_md": "hi"}},
        headers=bearer(admin),
    )
    item_id = await _deck(client, admin)
    assert (
        await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))
    ).status_code == 202

    wrong = await client.post(f"/api/v1/media/{blog.json()['id']}/produce", json=BRIEF, headers=bearer(admin))
    assert (wrong.status_code, wrong.json()["code"]) == (422, "media_wrong_kind")

    twice = await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))
    assert (twice.status_code, twice.json()["code"]) == (409, "av_already_running")


async def test_a_staff_save_is_refused_while_the_agent_is_working(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("produce-save@example.com", platform_admin=True)
    item_id = await _deck(client, admin)
    assert (
        await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))
    ).status_code == 202

    saved = await client.patch(
        f"/api/v1/media/{item_id}", json={"content": {"slides": []}}, headers=bearer(admin)
    )

    assert (saved.status_code, saved.json()["code"]) == (409, "media_being_produced")


async def test_stopping_ends_the_run_after_the_step_it_is_on_and_keeps_its_work(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("produce-stop@example.com", platform_admin=True)
    item_id = await _deck(client, admin)
    started = await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))

    stopping = await client.post(f"/api/v1/media/{item_id}/stop-produce", headers=bearer(admin))
    assert stopping.json()["content"]["review"]["run"]["stop"] is True

    job = _produce_job(db_session, "produce-stop@example.com", {})
    await job(started.json())

    content = (await client.get(f"/api/v1/media/by-id/{item_id}", headers=bearer(admin))).json()["content"]
    assert content["slides"] == PRODUCED["slides"]
    assert "status" not in content
    assert content["review"]["run"]["outcome"] == "stopped"
    assert [step["tool"] for step in content["review"]["run"]["steps"]] == ["write_draft"]


async def test_a_run_whose_worker_died_is_taken_over_and_its_old_job_writes_nothing_more(
    client: AsyncClient, make_actor, db_session
) -> None:  # type: ignore[no-untyped-def]
    import uuid
    from datetime import UTC, datetime, timedelta

    from app.features.identity import repository as identity_repository
    from app.features.media_production.service_produce import enqueue_produce

    admin = await make_actor("produce-takeover@example.com", platform_admin=True)
    item_id = await _deck(client, admin)
    first = await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))
    user = await identity_repository.user_by_email(db_session, "produce-takeover@example.com")

    second = await enqueue_produce(
        db_session,
        uuid.UUID(item_id),
        requested_by=user.id,
        brief=BRIEF["brief"],
        source_text=None,
        now=datetime.now(UTC) + timedelta(minutes=16),
    )

    assert second.content["review"]["run"]["id"] != first.json()["content"]["review"]["run"]["id"]

    old_job = _produce_job(db_session, "produce-takeover@example.com", {})
    await old_job(first.json())

    content = (await client.get(f"/api/v1/media/by-id/{item_id}", headers=bearer(admin))).json()["content"]
    assert content["status"] == "producing"
    assert "slides" not in content
    assert content["review"]["run"]["steps"] == []


async def test_a_run_that_fails_is_recorded_on_the_item(client: AsyncClient, make_actor, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("produce-fail@example.com", platform_admin=True)
    item_id = await _deck(client, admin)
    started = await client.post(f"/api/v1/media/{item_id}/produce", json=BRIEF, headers=bearer(admin))

    # The model fails on its first question.
    job = _produce_job(db_session, "produce-fail@example.com", {})
    await job(started.json())

    content = (await client.get(f"/api/v1/media/by-id/{item_id}", headers=bearer(admin))).json()["content"]
    assert content["status"] == "failed"
    assert content["review"]["error"]["step"] == "produce"
