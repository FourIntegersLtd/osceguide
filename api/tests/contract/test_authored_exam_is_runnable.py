"""An exam written through the API can actually be sat and marked.

`test_attempt_is_runnable.py` proves an attempt survives the worker contract,
but it arranges its exam and its station through the services. This one uses
nothing but HTTP, as a platform admin actually would: rubric, exam, station
template, station — each published before the next names it — and then a
candidate sits it and the transcript comes back marked.

That end-to-end join is the thing that could rot quietly. The authoring routes
could all answer 201 while producing something the renderer cannot render or
the marker cannot mark, and every test in `tests/http` would still pass,
because each of them stops at the boundary of its own slice.

The exam here is deliberately not one of the four the platform used to ship,
and its scale is deliberately not R/A/G: both were hard-coded until rubrics
became data, so an exam that could not have existed before is the honest test
of whether they are data now.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from tests.support.rubrics import MINIMAL_MARKING_LAYOUT
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

# A four-point scale, which the engine could not represent while RAG_SCALE was
# the only one it shipped.
RUBRIC = {
    "scale": ["fail", "borderline", "pass", "distinction"],
    "domains": [
        {
            "id": "clinical_reasoning",
            "label": "Clinical reasoning",
            "live": True,
            "competencies": [
                {
                    "id": "builds_a_differential",
                    "label": "Builds a differential",
                    "descriptors": {
                        "distinction": "Three plausible diagnoses, ranked, with reasons.",
                        "pass": "Two plausible diagnoses.",
                        "borderline": "One, unranked.",
                        "fail": "None offered.",
                    },
                }
            ],
        }
    ],
    "sections": [{"id": "actionable_feedback", "label": "Actionable feedback", "kind": "list"}],
}

TEMPLATE = {
    "schemaVersion": 1,
    "sections": [
        {
            "id": "main",
            "title": "Main",
            "blocks": [
                {
                    "id": "who_you_are",
                    "type": "longText",
                    "label": "Who you are",
                    "kind": "text",
                    "role": "persona",
                },
                {
                    "id": "why_you_came",
                    "type": "longText",
                    "label": "Why you came",
                    "kind": "text",
                    "role": "complaint",
                },
                {
                    "id": "your_history",
                    "type": "longText",
                    "label": "Your history",
                    "kind": "text",
                    "role": "history",
                },
                {
                    "id": "expected",
                    "type": "longText",
                    "label": "Expected answers",
                    "kind": "text",
                    "role": "examiner",
                },
            ],
        }
    ],
    "layout": {"persona": "patient"},
}

CONTENT = {
    "who_you_are": "Marek, 61, a retired bus driver.",
    "why_you_came": "I get short of breath walking to the shops.",
    "your_history": "Smoked forty years. Two admissions last winter.",
    "expected": "Should reach COPD and ask about smoking.",
}


def worker_headers() -> dict[str, str]:
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


async def test_an_exam_authored_over_http_can_be_sat_and_marked(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    from app.features.attempts.jobs import policy_for, score_attempt_now
    from app.features.attempts.models import Attempt
    from tests.support.fakes import FakeEvaluator

    admin = await make_actor("platform-admin@osceguide.com", platform_admin=True)

    # 1. The rubric. Nothing is marked against anything until this exists.
    rubric = await client.post(
        "/api/v1/platform/rubrics",
        json={
            "title": "MRCP PACES marking",
            "structure": RUBRIC,
            "system_prompt": "Mark this consultation against the rubric.",
            "pacing": {
                "total_seconds": 600,
                "history_seconds": 300,
                "introduction_seconds": 30,
                "safety_net_seconds": 90,
            },
            "marking_layout": MINIMAL_MARKING_LAYOUT,
        },
        headers=bearer(admin),
    )
    assert rubric.status_code == 201, rubric.text
    rubric_id = rubric.json()["id"]
    # The schema the model will be constrained by is derived, not written.
    derived = rubric.json()["versions"][0]["result_schema"]
    assert list(derived["properties"]) == ["clinical_reasoning", "actionable_feedback"]
    scored = derived["properties"]["clinical_reasoning"]["properties"]["builds_a_differential"]
    assert scored["properties"]["score"]["enum"] == ["fail", "borderline", "pass", "distinction"]
    assert "Three plausible diagnoses" in scored["description"], "the author's words reach the model"

    published_rubric = await client.post(
        f"/api/v1/platform/rubrics/{rubric_id}/versions/1/publish", headers=bearer(admin)
    )
    assert published_rubric.status_code == 200, published_rubric.text
    rubric_version_id = published_rubric.json()["id"]

    # 2. The exam, which cannot be published until it names that rubric.
    exam = await client.post(
        "/api/v1/platform/exams",
        json={
            "code": "mrcp-paces",
            "name": "MRCP PACES",
            "default_reading_seconds": 120,
            "default_simulation_seconds": 600,
            "rubric_version_id": rubric_version_id,
        },
        headers=bearer(admin),
    )
    assert exam.status_code == 201, exam.text
    assert exam.json()["status"] == "draft", "nothing may be built on it yet"
    exam_id = exam.json()["id"]

    published_exam = await client.post(f"/api/v1/platform/exams/{exam_id}/publish", headers=bearer(admin))
    assert published_exam.status_code == 200, published_exam.text
    # What a result will be recorded under is the rubric version's own id.
    assert published_exam.json()["framework_id"] == rubric_version_id

    # 3. The station's shape, then a station written to it.
    template = await client.post(
        "/api/v1/platform/station-templates",
        json={"title": "PACES station", "exam_code": "mrcp-paces", "structure": TEMPLATE},
        headers=bearer(admin),
    )
    assert template.status_code == 201, template.text
    published_template = await client.post(
        f"/api/v1/platform/station-templates/{template.json()['id']}/publish", headers=bearer(admin)
    )
    assert published_template.status_code == 200, published_template.text

    station = await client.post(
        "/api/v1/platform/stations",
        json={
            "title": "COPD exacerbation",
            "exam_code": "mrcp-paces",
            "content": CONTENT,
            "template_version_id": published_template.json()["id"],
        },
        headers=bearer(admin),
    )
    assert station.status_code == 201, station.text
    published_station = await client.post(
        f"/api/v1/platform/stations/{station.json()['id']}/versions/1/publish",
        headers=bearer(admin),
    )
    assert published_station.status_code == 200, published_station.text
    station_version_id = published_station.json()["id"]

    # 4. A candidate, entitled to the exam that did not exist a moment ago.
    candidate = await make_actor("paces-candidate@example.com")
    user = await identity_repo.user_by_email(db_session, "paces-candidate@example.com")
    assert user is not None
    await ent_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=uuid.UUID(exam_id),
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await db_session.flush()

    created = await client.post(
        "/api/v1/attempts",
        json={
            "kind": "practice",
            "exam_code": "mrcp-paces",
            "station_version_id": station_version_id,
        },
        headers=bearer(candidate),
    )
    assert created.status_code == 201, created.text
    attempt_id = created.json()["id"]

    # 5. The worker collects it. This is where an authoring mistake would show:
    #    a station the renderer cannot render produces no instructions at all.
    boot = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert boot.status_code == 200, boot.text
    instructions = boot.json()["attempt"]["definition"]["interaction_profile"]["instructions"]
    assert "retired bus driver" in instructions, "the template's blocks reached the prompt"
    assert "Should reach COPD" not in instructions, "examiner material never reaches the patient"
    assert "COPD exacerbation" in instructions, "the diagnosis is present but fenced"
    assert "<never_say>" in instructions

    # The worker is handed the scenario and never the marking policy.
    assert "evaluation_policy" not in boot.json()["attempt"]["definition"]

    # 6. The conversation, delivered.
    done = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={
            "attempt_id": attempt_id,
            "transcript": {
                "attempt_id": attempt_id,
                "messages": [
                    {
                        "message_id": "m0",
                        "seq": 0,
                        "role": "assistant",
                        "message": "I get short of breath on the stairs.",
                        "timestamp": NOW.isoformat(),
                    }
                ],
                "complete": True,
            },
        },
        headers=worker_headers(),
    )
    assert done.status_code in (200, 202), done.text

    # 7. Marking reads the rubric frozen onto the attempt, not a row that may
    #    since have changed — so a re-mark next year uses these words.
    attempt = await db_session.get(Attempt, uuid.UUID(attempt_id))
    assert attempt is not None
    framework_id, policy_version = policy_for(attempt)
    assert framework_id == rubric_version_id
    frozen = attempt.definition["evaluation_policy"]["rubric"]
    assert frozen["framework"]["scale"] == ["fail", "borderline", "pass", "distinction"]
    assert frozen["system_prompt"] == "Mark this consultation against the rubric."

    evaluator = FakeEvaluator(payload={"clinical_reasoning": {}, "model_used": "fake-model"})
    wrote = await score_attempt_now(
        db_session,
        uuid.UUID(attempt_id),
        evaluator=evaluator,
        policy_version=policy_version,
        framework_id=framework_id,
        now=NOW,
    )
    assert wrote is True
    # The marker was handed the whole rubric, not an id to look one up by.
    assert evaluator.calls[0]["rubric"]["framework"]["id"] == rubric_version_id

    # 8. And the candidate reads their result back.
    result = await client.get(f"/api/v1/attempts/{attempt_id}/result", headers=bearer(candidate))
    assert result.status_code == 200, result.text
    assert result.json()["items"][0]["framework_id"] == rubric_version_id
