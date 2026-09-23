"""Coverage remains private, grounded, durable, and separate from marks."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.features.attempts import llm_clients, repository, repository_coverage, repository_transcript
from app.features.attempts.jobs import SCORING_TASK
from app.features.attempts.jobs_coverage import TASK as COVERAGE_TASK
from app.features.attempts.models import Attempt
from app.features.attempts.schemas import TranscriptMessageIn
from app.features.attempts.service_coverage import update_coverage
from app.features.attempts.service_worker import accept_chunk, complete_interaction
from tests.http.test_attempt_material_routes import NOW, _entitled_attempt
from tests.support.rubrics import frozen_definition
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_live_evidence_is_grounded_and_owner_only(client, db_session, make_actor, monkeypatch):
    token = await make_actor("coverage@example.com")
    other = await make_actor("coverage-other@example.com")
    sat = await _entitled_attempt(db_session, "coverage@example.com")
    definition = frozen_definition(str(sat.attempt_id))
    await repository.freeze_definition(db_session, sat.attempt_id, definition=definition, at=NOW)
    await accept_chunk(
        db_session,
        sat.attempt_id,
        body_attempt_id=str(sat.attempt_id),
        message=TranscriptMessageIn(
            role="user",
            message="What brought you in today?",
            timestamp=NOW,
            message_id="first",
            seq=0,
        ),
    )
    call = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        refusal=None,
                        content=json.dumps(
                            {
                                "newly_demonstrated": [
                                    {
                                        "competency_id": "opens_well",
                                        "state": "covered",
                                        "quote": "What brought you in today?",
                                        "seq": 0,
                                    }
                                ]
                            }
                        ),
                    )
                )
            ]
        )
    )
    monkeypatch.setattr(
        llm_clients,
        "primary_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=call)),
        ),
    )
    await update_coverage(db_session, sat.attempt_id)
    snapshot = await repository_coverage.read(db_session, sat.attempt_id)
    assert snapshot and len(snapshot["items"]) == 1
    await update_coverage(db_session, sat.attempt_id)
    assert call.call_count == 1
    await db_session.commit()
    url = f"/api/v1/attempts/{sat.attempt_id}/coverage"
    assert (await client.get(url, headers=bearer(other))).status_code == 403
    response = await client.get(url, headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["label"] == "Opens well"
    assert response.json()["items"][0]["state"] == "covered"
    assert await repository_transcript.results_for(db_session, sat.attempt_id) == []


async def test_unrendered_attempt_has_no_invented_coverage(client, db_session, make_actor):
    token = await make_actor("coverage-empty@example.com")
    sat = await _entitled_attempt(db_session, "coverage-empty@example.com")
    response = await client.get(f"/api/v1/attempts/{sat.attempt_id}/coverage", headers=bearer(token))
    assert response.status_code == 200
    assert response.json() == {"supported": False, "items": [], "last_seq": -1}


async def _jobs(session, attempt_id) -> list[tuple[str, str]]:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    rows = await session.execute(
        text("SELECT task_name, status FROM procrastinate_jobs WHERE args->>'attempt_id' = :id ORDER BY id"),
        {"id": str(attempt_id)},
    )
    return [(str(row[0]), str(row[1])) for row in rows]


async def test_the_nudges_a_session_leaves_behind_coalesce_into_one(client, db_session, make_actor):
    """Turns and the end of the session all ask for coverage; the queue holds one job.

    A duplicate queueing lock is the lock working, not an error to report: the
    job still waiting recomputes from whatever the transcript holds when it
    starts. Raised instead, it aborted the transaction that defers the marking
    beside it, so a session that streamed normally finished unmarked.
    """
    email = "coverage-coalesce@example.com"
    await make_actor(email)
    sat = await _entitled_attempt(db_session, email)
    await repository.freeze_definition(
        db_session, sat.attempt_id, definition=frozen_definition(str(sat.attempt_id)), at=NOW
    )
    attempt = await db_session.get(Attempt, sat.attempt_id)
    assert attempt is not None

    for seq in range(3):
        await accept_chunk(
            db_session,
            sat.attempt_id,
            body_attempt_id=str(sat.attempt_id),
            message=TranscriptMessageIn(
                role="user",
                message="Any chest pain since yesterday?",
                timestamp=NOW,
                message_id=f"t{seq}",
                seq=seq,
            ),
        )
    await complete_interaction(db_session, attempt, now=NOW)

    assert await _jobs(db_session, sat.attempt_id) == [
        (COVERAGE_TASK, "todo"),
        (SCORING_TASK, "todo"),
    ]
