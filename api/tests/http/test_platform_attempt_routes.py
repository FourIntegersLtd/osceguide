"""The support view of attempts: why has this person no feedback?

Four causes, four different rows, one screen. Each test here stages one of
the causes the way production produces it — through the worker routes, not by
editing rows — and asserts the console can tell it from the others.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository
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
