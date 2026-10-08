"""A new exam is data, not code (rubric-templates plan §9).

An institution authors a rubric nothing in the codebase has seen: an integer
1..5 rating, one domain of three competencies (score, evidence, missed), a
domain-level strengths list, a narrative summary, and a pass that needs every
domain to clear its own line. Publishing it must be enough for every consumer
of a mark to work: the derived result schema, the engine's framework and its
score validation, the stored totals, the feedback and performance reads, and
the sitting report's CSV row. Every expected value is written out by hand.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from osce_assessment.contracts import CompetencyFramework
from osce_assessment.contracts.framework import InvalidScoreError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.attempts import repository as attempts_repo
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.domain import Status
from app.features.catalog import service_authoring as catalog_authoring
from app.features.identity import repository as identity_repo
from app.features.rubrics import domain as rubric_domain
from app.features.rubrics import schema_builder
from app.features.rubrics import service as rubrics
from app.features.sittings.models import Circuit, Sitting, Slot
from app.features.stations.models import Station, StationVersion
from tests.support.rubrics import PACING, SYSTEM_PROMPT
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

PUBLISHED_AT = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)

WARD_ROUND_RUBRIC: dict[str, Any] = {
    "schemaVersion": 2,
    "instructions": "Feedback on one teaching-ward round.",
    "rating": {"kind": "range", "minimum": 1, "maximum": 5, "step": "integer", "field": "score"},
    "sections": [
        {
            "id": "ward_round",
            "title": "Ward round",
            "kind": "domain",
            "instructions": "How the round was led.",
            "competencies": [
                {"id": "prioritises", "label": "Prioritises the sickest patient"},
                {"id": "delegates", "label": "Delegates clearly"},
                {"id": "documents", "label": "Documents the plan"},
            ],
            "competencyFields": [
                {"id": "score", "label": "Score", "type": "rating", "role": "rating"},
                {
                    "id": "evidence",
                    "label": "Evidence",
                    "type": "list",
                    "required": False,
                    "role": "evidence",
                },
                {
                    "id": "missed",
                    "label": "Missed",
                    "type": "list",
                    "required": False,
                    "role": "improvement",
                },
            ],
            "fields": [
                {
                    "id": "strengths",
                    "label": "Strengths",
                    "type": "list",
                    "required": False,
                    "role": "strength",
                }
            ],
        },
        {
            "id": "summary",
            "title": "Summary",
            "kind": "section",
            "instructions": "The round in a few sentences.",
            "fields": [{"id": "narrative", "label": "Narrative", "type": "longText", "role": "explanation"}],
        },
    ],
    "display": {
        "domain": {"aggregate": "sum", "passAtLeast": 9},
        "total": {"aggregate": "sum", "passAtLeast": 9, "requireEveryDomain": True},
        "tones": [
            {"atLeast": 0.8, "tone": "good"},
            {"atLeast": 0.6, "tone": "fair"},
            {"atLeast": 0, "tone": "poor"},
        ],
    },
}


def _string_list(title: str) -> dict[str, Any]:
    """An optional list of short texts, titled as the author labelled the field."""
    return {"type": "array", "items": {"type": "string"}, "title": title}


def _competency_schema(label: str) -> dict[str, Any]:
    """What the engine must return for one competency: an integer score, and two optional lists."""
    return {
        "type": "object",
        "title": label,
        "description": label,
        "additionalProperties": False,
        "required": ["score"],
        "properties": {
            "score": {"type": "integer", "maximum": 5, "minimum": 1, "title": "Score"},
            "evidence": _string_list("Evidence"),
            "missed": _string_list("Missed"),
        },
    }


EXPECTED_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Feedback on one teaching-ward round.",
    "additionalProperties": False,
    "required": ["ward_round", "summary"],
    "properties": {
        "ward_round": {
            "type": "object",
            "title": "Ward round",
            "description": "How the round was led.",
            "additionalProperties": False,
            "required": ["prioritises", "delegates", "documents"],
            "properties": {
                "prioritises": _competency_schema("Prioritises the sickest patient"),
                "delegates": _competency_schema("Delegates clearly"),
                "documents": _competency_schema("Documents the plan"),
                "strengths": _string_list("Strengths"),
            },
        },
        "summary": {
            "type": "object",
            "title": "Summary",
            "description": "The round in a few sentences.",
            "additionalProperties": False,
            "required": ["narrative"],
            "properties": {"narrative": {"type": "string", "title": "Narrative"}},
        },
    },
}

# One marked round: 4 + 3 + 2 = 9 of 15, exactly the pass line; the 2 is
# under the 0.6 "fair" tone, so it is the one critical concern.
MARKED_ROUND: dict[str, Any] = {
    "ward_round": {
        "prioritises": {"score": 4, "evidence": ["Saw bed 3 first"], "missed": []},
        "delegates": {"score": 3, "evidence": [], "missed": ["Named no owner for bloods"]},
        "documents": {"score": 2, "evidence": [], "missed": ["No plan written"]},
        "strengths": ["Calm under pressure"],
    },
    "summary": {"narrative": "A safe round with a thin plan."},
}


async def _institution(client: AsyncClient, make_actor) -> tuple[uuid.UUID, str]:  # type: ignore[no-untyped-def]
    """An institution and its owner's token, created the way a platform admin does."""
    root = await make_actor("root-ward@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": "ward", "name": "Ward", "org_type": "institution"},
        headers=bearer(root),
    )
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        "admin-ward@example.com",
        memberships=(Membership(org_id=org_id, org_slug="ward", role="owner"),),
        active_org_slug="ward",
    )
    return org_id, admin


async def test_an_authored_rubric_marks_end_to_end_with_no_code_change(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await _institution(client, make_actor)

    # Author and publish: the rubric and the exam are rows, nothing more.
    rubric = await rubrics.create_rubric(
        db_session,
        org_id,
        title="Ward round",
        structure=WARD_ROUND_RUBRIC,
        system_prompt=SYSTEM_PROMPT,
        pacing=PACING,
    )
    version = await rubrics.publish_version(db_session, org_id, rubric.id, 1, actor=None, now=PUBLISHED_AT)
    version_id = version.id
    exam = await catalog_authoring.create_exam(
        db_session,
        org_id,
        code="ward-round",
        name="Ward round",
        default_reading_seconds=60,
        default_simulation_seconds=600,
        rubric_version_id=version_id,
    )
    exam_id = exam.id
    await catalog_authoring.publish_exam(db_session, exam_id, org_id)

    # The derived schema, and the engine's framework, come from the structure alone.
    structure = rubric_domain.parse_structure(WARD_ROUND_RUBRIC)
    assert schema_builder.derive_result_schema(structure) == EXPECTED_RESULT_SCHEMA
    assert rubric_domain.resolved_display(structure)["total"] == {
        "aggregate": "sum",
        "max": 15,
        "passAtLeast": 9,
        "requireEveryDomain": True,
    }
    framework = CompetencyFramework.model_validate(
        rubric_domain.framework_payload(
            framework_id=str(version_id),
            label="Ward round",
            version="1",
            structure=structure,
            system_prompt=SYSTEM_PROMPT,
        )
    )
    assert framework.competency_ids == ("prioritises", "delegates", "documents")
    assert framework.field_roles == {
        "score": "rating",
        "evidence": "evidence",
        "missed": "improvement",
        "strengths": "strength",
        "narrative": "explanation",
    }
    framework.validate_scores({"prioritises": 4, "delegates": 3, "documents": 2})
    with pytest.raises(InvalidScoreError):
        framework.validate_scores({"prioritises": 6, "delegates": 3, "documents": 2})

    # A learner's marked attempt at the new exam.
    learner = await make_actor("ward-learner@example.com")
    learner_user = await identity_repo.user_by_email(db_session, "ward-learner@example.com")
    assert learner_user is not None
    attempt = await attempts_repo.create_attempt(
        db_session, kind="practice", user_id=learner_user.id, exam_id=exam_id
    )
    attempt_id = attempt.id
    await attempts_repo.set_status(db_session, attempt_id, status=Status.EVALUATED, at=PUBLISHED_AT)
    await transcripts.save_result(
        db_session,
        attempt_id,
        framework_id=str(version_id),
        policy_version="platform-default@1",
        payload=MARKED_ROUND,
        model_used="gpt-5-mini",
        at=PUBLISHED_AT,
    )
    await db_session.commit()

    feedback = await client.get(f"/api/v1/attempts/{attempt_id}/feedback", headers=bearer(learner))
    assert feedback.status_code == 200, feedback.text
    [marked] = feedback.json()["results"]
    totals = marked["totals"]
    assert (totals["total"], totals["max"]) == (9.0, 15.0)
    assert (totals["passed"], totals["critical_count"]) == (True, 1)
    assert feedback.json()["rubric"]["display"]["total"]["passAtLeast"] == 9

    performance = await client.get("/api/v1/me/performance", headers=bearer(learner))
    assert performance.status_code == 200, performance.text
    body = performance.json()
    assert body["exam_code"] == "ward-round"
    assert body["rating"]["kind"] == "range"
    assert body["display"]["total"]["max"] == 15
    assert [(domain["id"], domain["value"]) for domain in body["domains"]] == [("ward_round", 9.0)]
    assert (body["summary"]["pass_rate"], body["summary"]["critical_rate"]) == (1.0, 1.0)

    # The same rubric marks a sitting: a reviewer's 4, 3, 2 is the report's row.
    station = Station(owner_kind="org", org_id=org_id, exam_id=exam_id, title="Ward round")
    db_session.add(station)
    await db_session.flush()
    station_version = StationVersion(
        station_id=station.id, org_id=org_id, version=1, content={}, status="published"
    )
    db_session.add(station_version)
    sitting = Sitting(org_id=org_id, name="Ward finals", mode="exam", rubric_version_id=version_id)
    db_session.add(sitting)
    await db_session.flush()
    sitting_id = sitting.id
    circuit = Circuit(org_id=org_id, sitting_id=sitting_id, name="C")
    db_session.add(circuit)
    await db_session.flush()
    slot = Slot(
        org_id=org_id,
        circuit_id=circuit.id,
        slot_index=0,
        trainee_id=learner_user.id,
        station_version_id=station_version.id,
    )
    db_session.add(slot)
    await db_session.commit()
    slot_id = slot.id

    form = await client.get(f"/api/v1/orgs/ward/slots/{slot_id}/reviews", headers=bearer(admin))
    assert form.status_code == 200, form.text

    reviewed = await client.put(
        f"/api/v1/orgs/ward/slots/{slot_id}/reviews/mine",
        json={
            "field_values": {
                "ward_round.prioritises.score": 4,
                "ward_round.delegates.score": 3,
                "ward_round.documents.score": 2,
            },
            "status": "completed",
        },
        headers=bearer(admin),
    )
    assert reviewed.status_code == 200, reviewed.text

    exported = await client.get(f"/api/v1/orgs/ward/sittings/{sitting_id}/report.csv", headers=bearer(admin))
    assert exported.status_code == 200, exported.text
    rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    [row] = rows
    # A range domain's ratings combine as their mean, 3; the overall is the
    # worst domain, the only one; 3 of 5 scores 60; and 9 of 15 clears the line.
    assert (row["email"], row["stations"], row["overall_rag"], row["score"], row["stations_passed"]) == (
        "ward-learner@example.com",
        "1",
        "3",
        "60",
        "1",
    )
