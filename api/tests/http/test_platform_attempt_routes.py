"""The support view of attempts: why has this person no feedback?

Four causes, four different rows, one screen. Each test here stages one of
the causes the way production produces it — through the worker routes, not by
editing rows — and asserts the console can tell it from the others.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import null, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository, service_platform_actions
from app.features.attempts.jobs import SCORING_TASK
from app.features.attempts.models import Attempt
from app.features.identity import repository as identity_repo
from tests.contract.test_worker_routes import DEFINITION, NOW, transcript, worker_headers
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_person_with_an_attempt(session: AsyncSession, email: str, *, frozen: bool = True):  # type: ignore[no-untyped-def]
    user = await identity_repo.create_user(session, email=email, name="C", password_hash=None)
    exam = await ensure_exam(session, "sca")
    attempt = await repository.create_attempt(
        session, kind="practice", user_id=user.id, exam_id=exam.id, room_name=f"room-{uuid.uuid4().hex[:6]}"
    )
    if frozen:
        await repository.freeze_definition(session, attempt.id, definition=DEFINITION, at=NOW)
    await session.flush()
    return user.id, attempt.id


async def bootstrap(client: AsyncClient, attempt_id: uuid.UUID) -> None:
    started = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert started.status_code == 200, started.text


async def deliver(client: AsyncClient, attempt_id: uuid.UUID) -> None:
    delivered = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={"attempt_id": str(attempt_id), "transcript": transcript(attempt_id)},
        headers=worker_headers(),
    )
    assert delivered.status_code == 202, delivered.text


async def test_a_delivered_transcript_shows_as_complete_with_its_marking_queued(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    user_id, attempt_id = await a_person_with_an_attempt(db_session, "sat@example.com")
    await bootstrap(client, attempt_id)
    await deliver(client, attempt_id)

    listed = await client.get(f"/api/v1/platform/users/{user_id}/attempts", headers=bearer(root))
    assert listed.status_code == 200, listed.text
    [row] = listed.json()["items"]
    assert row["id"] == str(attempt_id)
    assert row["user_id"] == str(user_id)
    assert row["status"] == "interaction_complete"
    assert row["transcript_complete"] is True
    assert row["transcript_delivered_at"] is not None
    assert row["result_policy_versions"] == []
    assert row["scoring_job"]["status"] == "todo"
    assert row["scoring_job"]["policy_version"] == "platform-default@1"


async def test_a_session_the_worker_never_finished_shows_no_transcript_and_no_job(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The commonest support case: the room opened and nothing came back."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    user_id, attempt_id = await a_person_with_an_attempt(db_session, "stuck@example.com")
    await bootstrap(client, attempt_id)

    listed = await client.get(f"/api/v1/platform/users/{user_id}/attempts", headers=bearer(root))
    [row] = listed.json()["items"]
    assert row["status"] == "running"
    assert row["transcript_complete"] is False
    assert row["scoring_job"] is None
    assert row["failed_reason"] is None


async def test_the_detail_counts_the_turns_and_lists_every_marking_job(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "detail@example.com")
    await bootstrap(client, attempt_id)
    await deliver(client, attempt_id)

    detail = await client.get(f"/api/v1/platform/attempts/{attempt_id}", headers=bearer(root))
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["has_definition"] is True
    assert body["definition_frozen_at"] is not None
    assert body["chunk_count"] == 2
    assert [job["status"] for job in body["jobs"]] == ["todo"]
    assert body["scoring_job"]["id"] == body["jobs"][0]["id"]


async def test_an_attempt_that_was_never_rendered_says_so(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """No frozen rubric means nothing can be marked, and the detail must not
    hide that behind a missing job."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "bare@example.com", frozen=False)

    detail = await client.get(f"/api/v1/platform/attempts/{attempt_id}", headers=bearer(root))
    assert detail.json()["has_definition"] is False
    assert detail.json()["chunk_count"] == 0


async def test_the_listing_narrows_to_one_status(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    user_id, first = await a_person_with_an_attempt(db_session, "two@example.com")
    exam = await ensure_exam(db_session, "sca")
    second = await repository.create_attempt(
        db_session, kind="practice", user_id=user_id, exam_id=exam.id, room_name="r2"
    )
    await db_session.flush()
    await bootstrap(client, first)

    running = await client.get(
        f"/api/v1/platform/users/{user_id}/attempts?status=running", headers=bearer(root)
    )
    assert [row["id"] for row in running.json()["items"]] == [str(first)]
    created = await client.get(
        f"/api/v1/platform/users/{user_id}/attempts?status=created", headers=bearer(root)
    )
    assert [row["id"] for row in created.json()["items"]] == [str(second.id)]
    nonsense = await client.get(
        f"/api/v1/platform/users/{user_id}/attempts?status=lost", headers=bearer(root)
    )
    assert nonsense.status_code == 422


async def test_an_unknown_account_is_not_an_empty_list(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    missing = await client.get(f"/api/v1/platform/users/{uuid.uuid4()}/attempts", headers=bearer(root))
    assert missing.status_code == 404
    assert missing.json()["code"] == "user_not_found"


async def test_only_a_platform_admin_reads_across_accounts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("curious@example.com")
    user_id, attempt_id = await a_person_with_an_attempt(db_session, "private@example.com")

    assert (
        await client.get(f"/api/v1/platform/users/{user_id}/attempts", headers=bearer(someone))
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/platform/attempts/{attempt_id}", headers=bearer(someone))
    ).status_code == 403


# --------------------------------------------------------------------------
# The fixes
# --------------------------------------------------------------------------


async def scoring_jobs(db_session: AsyncSession, attempt_id: uuid.UUID) -> list[str]:
    """The markings, not every job an attempt carries — live coverage queues beside them."""
    from sqlalchemy import text

    rows = await db_session.execute(
        text(
            "SELECT status FROM procrastinate_jobs "
            "WHERE args->>'attempt_id' = :id AND task_name = :task ORDER BY id"
        ),
        {"id": str(attempt_id), "task": SCORING_TASK},
    )
    return [str(r[0]) for r in rows]


async def mark_jobs_failed(db_session: AsyncSession, attempt_id: uuid.UUID) -> None:
    """Fail the marking, the way a worker exhausting its retries would."""
    from sqlalchemy import text

    await db_session.execute(
        text(
            "UPDATE procrastinate_jobs SET status = 'failed' "
            "WHERE args->>'attempt_id' = :id AND task_name = :task"
        ),
        {"id": str(attempt_id), "task": SCORING_TASK},
    )


async def test_a_migrated_attempt_without_a_frozen_rubric_is_frozen_then_marked(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "legacy@example.com")

    async def freeze_from_station(session: AsyncSession, attempt: Attempt, *, now: datetime) -> dict:
        """Stand in for the station render: freeze the standard definition."""
        await repository.freeze_definition(session, attempt.id, definition=DEFINITION, at=now)
        return DEFINITION

    monkeypatch.setattr(service_platform_actions, "render_definition", freeze_from_station)
    await bootstrap(client, attempt_id)
    await deliver(client, attempt_id)
    await mark_jobs_failed(db_session, attempt_id)
    # A migrated attempt never had its rubric frozen on it.
    await db_session.execute(update(Attempt).where(Attempt.id == attempt_id).values(definition=null()))

    response = await client.post(
        f"/api/v1/platform/attempts/{attempt_id}/rescore", json={}, headers=bearer(root)
    )

    assert response.status_code == 200, response.text
    assert response.json()["queued"] is True
    assert await scoring_jobs(db_session, attempt_id) == ["failed", "todo"]


async def test_a_failed_marking_can_be_queued_again_and_twice_is_once(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "unmarked@example.com")
    await bootstrap(client, attempt_id)
    await deliver(client, attempt_id)
    await mark_jobs_failed(db_session, attempt_id)

    first = await client.post(
        f"/api/v1/platform/attempts/{attempt_id}/rescore", json={}, headers=bearer(root)
    )
    assert first.status_code == 200, first.text
    assert first.json() == {"queued": True, "policy_version": "platform-default@1", "reason": None}
    assert await scoring_jobs(db_session, attempt_id) == ["failed", "todo"]

    second = await client.post(
        f"/api/v1/platform/attempts/{attempt_id}/rescore", json={}, headers=bearer(root)
    )
    assert second.json()["queued"] is False
    assert second.json()["reason"] == "already_queued"
    assert await scoring_jobs(db_session, attempt_id) == ["failed", "todo"]

    detail = await client.get(f"/api/v1/platform/attempts/{attempt_id}", headers=bearer(root))
    assert [job["status"] for job in detail.json()["jobs"]] == ["todo", "failed"]
    audit = await client.get("/api/v1/platform/audit?action=attempt.rescore_requested", headers=bearer(root))
    # Matched by summary rather than position. Both presses write inside the test's
    # one transaction, so their `now()` ties and the newest-first tie-break on a
    # random uuid id is a coin flip; in production they are separate transactions.
    assert {row["summary"]: row["meta"]["queued"] for row in audit.json()["items"]} == {
        "platform-default@1: queued": True,
        "platform-default@1: already queued": False,
    }


async def test_a_marked_attempt_is_not_marked_again_under_the_same_policy(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.attempts import repository_transcript as transcripts

    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "marked@example.com")
    await bootstrap(client, attempt_id)
    await deliver(client, attempt_id)
    await transcripts.save_result(
        db_session,
        attempt_id,
        framework_id="f",
        policy_version="platform-default@1",
        payload={"score": 1},
        model_used=None,
        at=NOW,
    )
    await db_session.flush()

    same = await client.post(f"/api/v1/platform/attempts/{attempt_id}/rescore", json={}, headers=bearer(root))
    assert same.json() == {
        "queued": False,
        "policy_version": "platform-default@1",
        "reason": "already_scored",
    }
    other = await client.post(
        f"/api/v1/platform/attempts/{attempt_id}/rescore",
        json={"policy_version": "review@2"},
        headers=bearer(root),
    )
    assert other.json()["queued"] is True
    assert other.json()["policy_version"] == "review@2"

    running_user, running = await a_person_with_an_attempt(db_session, "still@example.com")
    await bootstrap(client, running)
    refused = await client.post(f"/api/v1/platform/attempts/{running}/rescore", json={}, headers=bearer(root))
    assert refused.status_code == 409
    assert refused.json()["code"] == "invalid_attempt_state"
    _ = running_user


async def test_a_session_the_worker_never_finished_can_be_salvaged_from_its_turns(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from tests.contract.test_worker_routes import chunk

    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "dropped@example.com")
    await bootstrap(client, attempt_id)
    for i in range(2):
        posted = await client.post(
            f"/api/worker/attempts/{attempt_id}/transcript-chunks",
            json={
                "attempt_id": str(attempt_id),
                "message": chunk(f"m{i}", i, "user" if i % 2 == 0 else "assistant"),
            },
            headers=worker_headers(),
        )
        assert posted.status_code == 202, posted.text

    salvaged = await client.post(f"/api/v1/platform/attempts/{attempt_id}/salvage", headers=bearer(root))
    assert salvaged.status_code == 200, salvaged.text
    body = salvaged.json()
    assert body["status"] == "interaction_complete"
    assert body["transcript_complete"] is True
    assert body["chunk_count"] == 2
    assert body["scoring_job"]["status"] == "todo"
    assert await scoring_jobs(db_session, attempt_id) == ["todo"]

    again = await client.post(f"/api/v1/platform/attempts/{attempt_id}/salvage", headers=bearer(root))
    assert again.status_code == 409

    _, empty = await a_person_with_an_attempt(db_session, "silent@example.com")
    await bootstrap(client, empty)
    nothing = await client.post(f"/api/v1/platform/attempts/{empty}/salvage", headers=bearer(root))
    assert nothing.status_code == 409
    assert nothing.json()["code"] == "invalid_attempt_state"


async def test_a_stuck_attempt_can_be_failed_so_a_fresh_one_can_start(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    _, attempt_id = await a_person_with_an_attempt(db_session, "stuck2@example.com")
    await bootstrap(client, attempt_id)

    failed = await client.post(
        f"/api/v1/platform/attempts/{attempt_id}/fail",
        json={"reason": "room never connected"},
        headers=bearer(root),
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "failed"
    assert failed.json()["failed_reason"] == "admin:room never connected"

    terminal = await client.post(
        f"/api/v1/platform/attempts/{attempt_id}/fail", json={"reason": "again"}, headers=bearer(root)
    )
    assert terminal.status_code == 409
    audit = await client.get("/api/v1/platform/audit?action=attempt.failed_by_admin", headers=bearer(root))
    assert audit.json()["items"][0]["meta"]["from_status"] == "running"


async def test_the_fixes_are_refused_to_anybody_but_a_platform_admin(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    someone = await make_actor("curious2@example.com")
    _, attempt_id = await a_person_with_an_attempt(db_session, "victim@example.com")
    for path, body in (("rescore", {}), ("salvage", None), ("fail", {"reason": "x"})):
        response = await client.post(
            f"/api/v1/platform/attempts/{attempt_id}/{path}", json=body, headers=bearer(someone)
        )
        assert response.status_code == 403, path


async def test_an_exam_slot_attempt_names_its_sitting_and_a_practice_one_does_not(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Support asked about an exam attempt needs to know which sitting it belongs to (P-27)."""
    from sqlalchemy import select

    from app.features.attempts.models import Attempt
    from app.features.catalog.models import Exam
    from app.features.sittings.models import Slot
    from tests.http.test_results_routes import org_with_admin
    from tests.support.decisions import a_sitting_and_trainee

    root = await make_actor("root@osceguide.com", platform_admin=True)
    org_id, _ = await org_with_admin(client, make_actor)
    sitting_id, _ = await a_sitting_and_trainee(db_session, org_id)
    slot = (await db_session.execute(select(Slot).where(Slot.org_id == org_id))).scalars().one()
    exam_id = await db_session.scalar(select(Exam.id).where(Exam.code == "sca"))
    attempt = Attempt(
        kind="exam_slot",
        user_id=slot.trainee_id,
        org_id=org_id,
        exam_id=exam_id,
        slot_id=slot.id,
        status="running",
    )
    db_session.add(attempt)
    await db_session.flush()
    attempt_id = attempt.id
    _, practice_id = await a_person_with_an_attempt(db_session, "plain@example.com")

    sat = (await client.get(f"/api/v1/platform/attempts/{attempt_id}", headers=bearer(root))).json()
    plain = (await client.get(f"/api/v1/platform/attempts/{practice_id}", headers=bearer(root))).json()

    assert sat["sitting_id"] == str(sitting_id)
    assert sat["sitting_name"] == "Finals"
    assert plain["sitting_id"] is None
    assert plain["sitting_name"] is None
