"""Rubric structures for tests, and the calls that author one through the API.

Every test that needs something to be marked against needs a rubric now, the
way it used to need a seeded exam. These are the two shapes worth having: the
smallest thing that can be published, and one with the features a real rubric
uses — a live domain, descriptors on every point of the scale, and both kinds
of non-scoring section.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient

from tests.support.tokens import bearer

PACING: dict[str, int] = {
    "total_seconds": 720,
    "history_seconds": 360,
    "introduction_seconds": 30,
    "safety_net_seconds": 120,
}

SYSTEM_PROMPT = "You are marking a consultation. Fill every field of the schema."

MINIMAL_RUBRIC: dict[str, Any] = {
    "scale": ["R", "A", "G"],
    "domains": [
        {
            "id": "consulting",
            "label": "Consulting",
            "live": True,
            "competencies": [{"id": "opens_well", "label": "Opens well", "descriptors": {"G": "Does it."}}],
        }
    ],
    "sections": [{"id": "actionable_feedback", "label": "Actionable feedback", "kind": "list"}],
}

# The shape the platform's own rubrics actually take: some domains judged live
# and some only in hindsight, descriptors on every point of the scale, and a
# narrative section nobody scores.
FULL_RUBRIC: dict[str, Any] = {
    "scale": ["R", "A", "G"],
    "domains": [
        {
            "id": "global_skills",
            "label": "Global skills",
            "live": False,
            "competencies": [
                {
                    "id": "structures_consultation",
                    "label": "Structures the consultation",
                    "descriptors": {
                        "G": "Clear opening, systematic history, signposted throughout.",
                        "A": "Misses one element.",
                        "R": "Misses several, or the consultation has no shape.",
                    },
                },
                {"id": "avoids_repetition", "label": "Avoids repetition", "descriptors": {}},
            ],
        },
        {
            "id": "tasks",
            "label": "Tasks",
            "live": True,
            "competencies": [
                {
                    "id": "discovers_ice",
                    "label": "Discovers ideas, concerns and expectations",
                    "descriptors": {
                        "G": "All three, in the patient's words.",
                        "A": "One or two.",
                        "R": "None.",
                    },
                }
            ],
        },
    ],
    "sections": [
        {"id": "actionable_feedback", "label": "Actionable feedback", "kind": "list"},
        {
            "id": "clinical_analysis",
            "label": "Clinical analysis",
            "kind": "object",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["missed_history"],
                "properties": {"missed_history": {"type": "array", "items": {"type": "string"}}},
            },
        },
    ],
}


async def create_rubric(
    client: AsyncClient,
    token: str,
    *,
    org_slug: str | None = None,
    title: str = "Marking rubric",
    structure: dict[str, Any] | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    """Author a rubric and, by default, publish its first version.

    `org_slug=None` authors it as the platform; a slug authors it as that
    organisation. Returns the rubric, with `version_id` set to the version an
    exam or a feedback template should name.
    """
    base = "/api/v1/platform/rubrics" if org_slug is None else f"/api/v1/orgs/{org_slug}/rubrics"
    response = await client.post(
        base,
        json={
            "title": title,
            "structure": structure or MINIMAL_RUBRIC,
            "system_prompt": SYSTEM_PROMPT,
            "pacing": PACING,
        },
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    rubric = response.json()
    rubric["version_id"] = rubric["versions"][0]["id"]
    if publish:
        published = await client.post(f"{base}/{rubric['id']}/versions/1/publish", headers=bearer(token))
        assert published.status_code == 200, published.text
        rubric["version_id"] = published.json()["id"]
    return rubric


def frozen_rubric(framework_id: str | None = None) -> dict[str, Any]:
    """A marking snapshot as `rubrics.marking_snapshot` returns one.

    For tests that need an attempt which *can* be marked without going through
    a render. Scoring reads the rubric off the attempt's frozen definition —
    there is no framework id to look one up by any more — so an attempt with no
    snapshot is deliberately unmarkable.
    """
    from app.features.rubrics import domain

    framework_id = framework_id or str(uuid.uuid4())
    return {
        "framework": domain.framework_payload(
            framework_id=framework_id,
            label="Marking rubric",
            version="1",
            structure=domain.parse_structure(MINIMAL_RUBRIC),
            system_prompt=SYSTEM_PROMPT,
        ),
        "system_prompt": SYSTEM_PROMPT,
        "pacing": dict(PACING),
    }


def frozen_definition(attempt_id: str, *, framework_id: str | None = None) -> dict[str, Any]:
    """The whole definition an attempt needs before it can be marked."""
    from app.features.attempts import domain_definition

    rubric = frozen_rubric(framework_id)
    return domain_definition.definition_payload(
        attempt_id=attempt_id,
        framework_id=str(rubric["framework"]["id"]),
        scenario_source="library",
        scenario_id=attempt_id,
        scenario={"id": attempt_id, "source": "library", "title": "Station"},
        instructions="You are the patient.",
        greeting=None,
        mode="patient",
        policy_version="platform-default@1",
        primary_model="fake-model",
        at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        rubric=rubric,
    )


def rubric_with_domains(*domain_ids: str) -> dict[str, Any]:
    """A rubric whose domains are exactly these, for a test that selects them."""
    return {
        "scale": ["R", "A", "G"],
        "domains": [
            {
                "id": domain_id,
                "label": domain_id.replace("_", " ").title(),
                "live": False,
                "competencies": [{"id": f"{domain_id}_overall", "label": "Overall", "descriptors": {}}],
            }
            for domain_id in domain_ids
        ],
        "sections": [{"id": "actionable_feedback", "label": "Actionable feedback", "kind": "list"}],
    }


async def published_feedback_version(
    session: Any,
    org_id: Any,
    *,
    field_selection: dict[str, Any] | None = None,
    structure: dict[str, Any] | None = None,
) -> Any:
    """A published feedback template version an org may bind to a sitting.

    Built through the services rather than by hand: a template names the rubric
    version it narrows now, so constructing the rows directly means knowing
    about `owner_kind`, the check constraint and the FK. Tests that only need
    "a sitting can exist" should not have to.
    """
    from datetime import UTC, datetime

    from app.features.rubrics import service as rubric_service
    from app.features.rubrics import service_feedback

    now = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    rubric = await rubric_service.create_rubric(
        session,
        None,
        title="Platform rubric",
        structure=structure or MINIMAL_RUBRIC,
        system_prompt=SYSTEM_PROMPT,
        pacing=PACING,
    )
    published = await rubric_service.publish_version(session, None, rubric.id, 1, actor_id=None, now=now)
    template = await service_feedback.create_feedback_template(
        session,
        org_id,
        title="R",
        rubric_version_id=published.id,
        field_selection=field_selection or {},
    )
    version = await service_feedback.publish_feedback_template(
        session, org_id, template.id, actor_id=None, now=now
    )
    return version
