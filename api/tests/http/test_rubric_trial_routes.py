"""Trial-marking a draft rubric version over SSE (plan §8, Stage 4).

The evaluator is the fake; the real engine is proved by hand (verify-marking).
What these pin down is the stream's shape, that everything refusable is refused
before it opens, and that a trial stores nothing.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ports import Evaluator
from app.core.rate_limit import TRIAL_MARK
from app.features.attempts.errors import MarkerUnavailable
from app.features.attempts.evaluator import trial_evaluator
from app.features.attempts.models import Attempt
from app.features.results.models import CandidateResultRevision
from tests.http.test_mfa_routes import CountingRedis
from tests.http.test_rubrics_routes import member, seed_org
from tests.repository.test_scoring_job import completed_attempt
from tests.support.fakes import FakeEvaluator
from tests.support.rubrics import PACING, SYSTEM_PROMPT
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

PLATFORM_RUBRICS = "/api/v1/platform/rubrics"
TRANSCRIPT = "Doctor: Hello, what brings you in today?\nPatient: I've had chest pain since this morning."
BLANK_MARKS: dict[str, Any] = {
    "domain_1": {
        "competency_1": {"score": "A", "evidence": "Asked an open question.", "explanation": "A fair start."}
    }
}


def stream_frames(response: Response) -> list[tuple[str, dict[str, Any]]]:
    """Every frame of an SSE body that has closed, as (event, decoded data)."""
    frames: list[tuple[str, dict[str, Any]]] = []
    for block in response.text.split("\n\n"):
        event = next(
            (line[len("event: ") :] for line in block.splitlines() if line.startswith("event: ")), ""
        )
        data = "".join(line[len("data: ") :] for line in block.splitlines() if line.startswith("data: "))
        if event:
            frames.append((event, json.loads(data)))
    return frames


@pytest.fixture
def fake_marker(app):  # type: ignore[no-untyped-def]
    """The trial's evaluator, replaced by one that answers the blank rubric's marks at once."""
    marker = FakeEvaluator(payload={**BLANK_MARKS, "model_used": "fake-model"})
    app.dependency_overrides[trial_evaluator] = lambda: marker
    yield marker
    app.dependency_overrides.pop(trial_evaluator, None)


async def blank_draft(client: AsyncClient, token: str, prefix: str = PLATFORM_RUBRICS) -> str:
    """A new rubric started from blank, left as a draft; its id."""
    response = await client.post(f"{prefix}/copy", json={}, headers=bearer(token))
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def row_counts(session: AsyncSession) -> tuple[int, int]:
    """How many attempts and results exist: a trial must add to neither."""
    attempts = await session.scalar(select(func.count()).select_from(Attempt))
    results = await session.scalar(select(func.count()).select_from(CandidateResultRevision))
    return int(attempts or 0), int(results or 0)


async def test_a_draft_is_trial_marked_against_a_pasted_transcript(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, fake_marker: FakeEvaluator, db_session: AsyncSession
) -> None:
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric_id = await blank_draft(client, admin)
    before = await row_counts(db_session)

    response = await client.post(
        f"{PLATFORM_RUBRICS}/{rubric_id}/versions/1/trial",
        json={"transcript": TRANSCRIPT},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = stream_frames(response)
    assert [(event, data.get("status")) for event, data in frames] == [
        ("connected", None),
        ("snapshot", "marking"),
        ("snapshot", "marked"),
    ]
    marked = frames[-1][1]
    assert marked["turn_count"] == 2
    assert marked["marks"] == BLANK_MARKS
    assert marked["model_used"] == "fake-model"
    assert marked["error"] is None
    assert marked["totals"]["domains"][0]["counts"] == {"G": 0, "A": 1, "R": 0}
    assert fake_marker.calls[0]["policy_version"] == "trial"
    assert fake_marker.calls[0]["turns"] == 2
    assert await row_counts(db_session) == before


async def test_a_platform_trial_can_mark_a_platform_attempts_transcript(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, fake_marker: FakeEvaluator, db_session: AsyncSession
) -> None:
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric_id = await blank_draft(client, admin)
    attempt_id = await completed_attempt(db_session)

    response = await client.post(
        f"{PLATFORM_RUBRICS}/{rubric_id}/versions/1/trial",
        json={"attempt_id": str(attempt_id)},
        headers=bearer(admin),
    )

    assert response.status_code == 200, response.text
    assert stream_frames(response)[-1][1]["status"] == "marked"
    assert (fake_marker.calls[0]["turns"], stream_frames(response)[-1][1]["turn_count"]) == (2, 2)


async def test_a_marker_that_fails_ends_the_stream_with_why(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, app
) -> None:
    app.dependency_overrides[trial_evaluator] = lambda: FakeEvaluator(fail_times=1)
    try:
        admin = await make_actor("admin@osceguide.com", platform_admin=True)
        rubric_id = await blank_draft(client, admin)

        response = await client.post(
            f"{PLATFORM_RUBRICS}/{rubric_id}/versions/1/trial",
            json={"transcript": TRANSCRIPT},
            headers=bearer(admin),
        )
    finally:
        app.dependency_overrides.pop(trial_evaluator, None)

    assert response.status_code == 200, response.text
    last = stream_frames(response)[-1][1]
    assert (last["status"], last["marks"], last["totals"]) == ("failed", None, None)
    assert last["error"]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"transcript": "no speaker here"}, "invalid_trial_transcript"),
        ({"transcript": "Patient: I only talk to myself."}, "invalid_trial_transcript"),
        ({}, "invalid_trial_transcript"),
        ({"transcript": TRANSCRIPT, "attempt_id": str(uuid.uuid4())}, "invalid_trial_transcript"),
    ],
    ids=["no speaker", "no candidate", "neither source", "both sources"],
)
async def test_a_transcript_with_nothing_to_mark_is_refused_before_the_stream(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, fake_marker: FakeEvaluator, body: dict[str, Any], code: str
) -> None:
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric_id = await blank_draft(client, admin)

    response = await client.post(
        f"{PLATFORM_RUBRICS}/{rubric_id}/versions/1/trial", json=body, headers=bearer(admin)
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == code
    assert fake_marker.calls == []


async def test_a_draft_that_cannot_mark_yet_is_refused_with_its_problems(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, fake_marker: FakeEvaluator
) -> None:
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    created = await client.post(
        PLATFORM_RUBRICS,
        json={
            "title": "Half done",
            "structure": {"schemaVersion": 2, "rating": {"kind": "rag"}, "sections": []},
            "system_prompt": SYSTEM_PROMPT,
            "pacing": PACING,
        },
        headers=bearer(admin),
    )
    assert created.status_code == 201, created.text

    response = await client.post(
        f"{PLATFORM_RUBRICS}/{created.json()['id']}/versions/1/trial",
        json={"transcript": TRANSCRIPT},
        headers=bearer(admin),
    )

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "invalid_rubric"
    assert response.json()["details"]["errors"] == [
        {
            "path": "sections",
            "message": "A rubric needs at least one section: it would ask the marker for nothing.",
        }
    ]


async def test_an_org_trials_only_its_own_rubrics_and_attempts(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, fake_marker: FakeEvaluator, db_session: AsyncSession
) -> None:
    platform_admin = await make_actor("admin@osceguide.com", platform_admin=True)
    platform_rubric_id = await blank_draft(client, platform_admin)
    platform_attempt_id = str(await completed_attempt(db_session))
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")
    trainee = await member(make_actor, org_id, "kings", "trainee")
    own_rubric_id = await blank_draft(client, admin, prefix="/api/v1/orgs/kings/rubrics")
    org_trial = "/api/v1/orgs/kings/rubrics/{rubric_id}/versions/1/trial"

    own = await client.post(
        org_trial.format(rubric_id=own_rubric_id), json={"transcript": TRANSCRIPT}, headers=bearer(admin)
    )
    platform_rubric = await client.post(
        org_trial.format(rubric_id=platform_rubric_id), json={"transcript": TRANSCRIPT}, headers=bearer(admin)
    )
    platform_attempt = await client.post(
        org_trial.format(rubric_id=own_rubric_id),
        json={"attempt_id": platform_attempt_id},
        headers=bearer(admin),
    )
    as_trainee = await client.post(
        org_trial.format(rubric_id=own_rubric_id), json={"transcript": TRANSCRIPT}, headers=bearer(trainee)
    )

    assert stream_frames(own)[-1][1]["status"] == "marked"
    assert (platform_rubric.status_code, platform_rubric.json()["code"]) == (404, "rubric_not_found")
    assert (platform_attempt.status_code, platform_attempt.json()["code"]) == (404, "attempt_not_found")
    assert as_trainee.status_code == 403


async def test_over_the_trial_allowance_is_refused_before_the_stream_opens(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, fake_marker: FakeEvaluator, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 20-an-hour allowance (`TRIAL_MARK`) is counted per platform admin.

    `prepare_trial` counts it last, so every call up to the allowance still
    marks; only the one over it is refused, and refused as a plain JSON 429
    with no stream ever opened for it (not an SSE body, and the marker is
    never called for that one)."""
    counter = CountingRedis()
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: counter)
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    rubric_id = await blank_draft(client, admin)
    url = f"{PLATFORM_RUBRICS}/{rubric_id}/versions/1/trial"

    for _ in range(TRIAL_MARK.allowance):
        allowed = await client.post(url, json={"transcript": TRANSCRIPT}, headers=bearer(admin))
        assert allowed.status_code == 200, allowed.text
    calls_within_allowance = len(fake_marker.calls)

    refused = await client.post(url, json={"transcript": TRANSCRIPT}, headers=bearer(admin))

    assert refused.status_code == 429, refused.text
    assert refused.json()["code"] == "too_many_requests"
    assert not refused.headers["content-type"].startswith("text/event-stream")
    assert calls_within_allowance == TRIAL_MARK.allowance
    assert len(fake_marker.calls) == TRIAL_MARK.allowance  # the refused call never reached the marker


async def test_a_platform_admin_lists_trial_candidates_outside_any_org(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    attempt_id = await completed_attempt(db_session)

    response = await client.get(f"{PLATFORM_RUBRICS}/trial-candidates", headers=bearer(admin))

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert str(attempt_id) in [item["id"] for item in items]
    row = next(item for item in items if item["id"] == str(attempt_id))
    assert row["turn_count"] == 2
    assert row["candidate_label"]


async def test_an_org_admin_only_sees_its_own_orgs_attempts_as_trial_candidates(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    platform_attempt_id = str(await completed_attempt(db_session))
    org_id = await seed_org(client, make_actor)
    admin = await member(make_actor, org_id, "kings", "admin")
    trainee = await member(make_actor, org_id, "kings", "trainee")

    response = await client.get("/api/v1/orgs/kings/rubrics/trial-candidates", headers=bearer(admin))
    as_trainee = await client.get("/api/v1/orgs/kings/rubrics/trial-candidates", headers=bearer(trainee))

    assert response.status_code == 200, response.text
    assert platform_attempt_id not in [item["id"] for item in response.json()["items"]]
    assert as_trainee.status_code == 403


async def test_an_attempt_with_no_transcript_is_not_offered_as_a_trial_candidate(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    admin = await make_actor("admin@osceguide.com", platform_admin=True)
    empty_attempt_id = await completed_attempt(db_session, turns=0)

    response = await client.get(f"{PLATFORM_RUBRICS}/trial-candidates", headers=bearer(admin))

    assert response.status_code == 200, response.text
    assert str(empty_attempt_id) not in [item["id"] for item in response.json()["items"]]


async def test_no_marker_installed_is_refused_before_the_stream_opens(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, app
) -> None:
    """`trial_evaluator` raises `MarkerUnavailable` (503) when the engine
    cannot be built; FastAPI resolves that dependency before the route body
    runs, so this fails before `prepare_trial` and before any stream opens."""

    def unavailable() -> Evaluator:
        raise MarkerUnavailable("The osce_assessment engine is not installed.")

    app.dependency_overrides[trial_evaluator] = unavailable
    try:
        admin = await make_actor("admin@osceguide.com", platform_admin=True)
        rubric_id = await blank_draft(client, admin)

        response = await client.post(
            f"{PLATFORM_RUBRICS}/{rubric_id}/versions/1/trial",
            json={"transcript": TRANSCRIPT},
            headers=bearer(admin),
        )
    finally:
        app.dependency_overrides.pop(trial_evaluator, None)

    assert response.status_code == 503, response.text
    assert response.json()["code"] == "marker_unavailable"
    assert not response.headers["content-type"].startswith("text/event-stream")
