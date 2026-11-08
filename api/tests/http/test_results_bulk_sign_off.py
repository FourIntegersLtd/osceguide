"""The sheet-level sign-off: every decided candidate of a sitting, or none."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_results_routes import org_with_admin, url
from tests.support.decisions import a_sitting_and_trainee, seat_candidate
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

DECISION = {"assessment_outcome": "pass", "recruitment_outcome": "hired", "rationale": "Met the standard."}


def bulk(sitting: uuid.UUID) -> str:
    return f"/api/v1/orgs/kings/sittings/{sitting}/decisions/sign-off"


async def a_second_candidate(db_session: AsyncSession, org_id: uuid.UUID, sitting: uuid.UUID) -> uuid.UUID:
    from app.features.roster.models import Trainee

    row = Trainee(org_id=org_id, email=f"c{uuid.uuid4().hex[:8]}@example.com")
    db_session.add(row)
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting, row.id)
    return row.id


async def test_one_call_signs_off_every_draft_and_names_the_signer(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, first = await a_sitting_and_trainee(db_session, org_id)
    second = await a_second_candidate(db_session, org_id, sitting)
    for trainee in (first, second):
        await client.put(url(sitting, trainee), json=DECISION, headers=bearer(admin))

    response = await client.post(bulk(sitting), headers=bearer(admin))

    assert response.status_code == 200, response.text
    signed = response.json()["signed_off"]
    assert sorted(entry["trainee_id"] for entry in signed) == sorted([str(first), str(second)])
    assert {entry["decision"]["workflow_state"] for entry in signed} == {"signed_off"}
    assert {entry["decision"]["signed_off_by_name"] for entry in signed} == {"admin-kings@example.com"}
    read = await client.get(url(sitting, first), headers=bearer(admin))
    assert read.json()["signed_off_by_name"] == "admin-kings@example.com"
    assert read.json()["signed_off_at"] is not None
    report = await client.get(f"/api/v1/orgs/kings/sittings/{sitting}/report", headers=bearer(admin))
    named = {c["decision"]["signed_off_by_name"] for c in report.json()["candidates"] if c["decision"]}
    assert named == {"admin-kings@example.com"}


async def test_a_candidate_with_no_decision_refuses_the_sheet_and_signs_nobody(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, decided = await a_sitting_and_trainee(db_session, org_id)
    await a_second_candidate(db_session, org_id, sitting)
    await client.put(url(sitting, decided), json=DECISION, headers=bearer(admin))

    refused = await client.post(bulk(sitting), headers=bearer(admin))

    assert refused.status_code == 409
    assert refused.json()["code"] == "decisions_incomplete"
    assert refused.json()["message"] == "1 candidate has no decision yet"
    still = await client.get(url(sitting, decided), headers=bearer(admin))
    assert (still.json()["workflow_state"], still.json()["signed_off_by_name"]) == ("draft", None)


async def test_an_exam_candidate_without_a_hiring_outcome_refuses_the_sheet(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    await client.put(
        url(sitting, trainee),
        json={"assessment_outcome": "pass", "rationale": "Met the standard."},
        headers=bearer(admin),
    )

    refused = await client.post(bulk(sitting), headers=bearer(admin))

    assert refused.status_code == 409
    assert refused.json()["message"] == "1 candidate has no decision yet"


async def test_a_supervisor_may_not_sign_off_the_sheet(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await org_with_admin(client, make_actor)
    sitting, _ = await a_sitting_and_trainee(db_session, org_id)
    supervisor = await make_actor(
        "sup-sheet@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    response = await client.post(bulk(sitting), headers=bearer(supervisor))

    assert response.status_code == 403


async def test_another_orgs_sitting_is_not_found(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    other_id, _ = await org_with_admin(client, make_actor, slug="barts")
    theirs, _ = await a_sitting_and_trainee(db_session, other_id)

    response = await client.post(bulk(theirs), headers=bearer(admin))

    assert response.status_code == 404
    assert response.json()["code"] == "sitting_not_found"
