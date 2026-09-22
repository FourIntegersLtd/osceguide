"""Coverage remains private, grounded, durable, and separate from marks."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.features.attempts import llm_clients, repository, repository_coverage, repository_transcript
from app.features.attempts.schemas import TranscriptMessageIn
from app.features.attempts.service_coverage import update_coverage
from app.features.attempts.service_worker import accept_chunk
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
