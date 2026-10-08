"""Oracle: `b2b-api/tests/test_session_cohort_report.py`.

What a GP lead opens after an examination to decide who to review first. The
ranking rule is the one that matters and it is not the obvious one: completion
comes before score, because a candidate who sat three of five stations has a
problem nobody has looked at, while one who scored badly has at least been
assessed.

The arithmetic underneath is pinned separately, against the legacy helpers, in
`tests/unit/test_cohort_scoring_oracle.py`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_org_read_models import a_circuit, a_user
from tests.support.sittings import a_sitting, org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def a_candidate(
    client: AsyncClient,
    admin: str,
    db_session: AsyncSession,
    *,
    sitting_id: str,
    stations: list[str],
    email: str,
) -> dict:
    """One exam circuit: one candidate through every station (C1)."""
    user_id = await a_user(db_session, email)
    circuit = await a_circuit(
        client,
        admin,
        "kings",
        sitting_id=sitting_id,
        trainee_ids=[str(user_id)],
        station_version_ids=stations,
    )
    return {"user_id": str(user_id), "circuit": circuit, "email": email}


async def mark(client: AsyncClient, admin: str, slot_id: str, rag: str) -> None:
    """A completed review of one slot, through the route a reviewer uses."""
    response = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"consulting.score": rag}, "status": "completed"},
        headers=bearer(admin),
    )
    assert response.status_code == 200, response.text


async def finish(db_session: AsyncSession, slot_id: str) -> None:
    """Mark the station as sat.

    Written directly: the candidate finishing a station is the worker's doing,
    and this is about what the report makes of it afterwards.
    """
    from sqlalchemy import update

    from app.features.sittings.models import Slot

    await db_session.execute(
        update(Slot).where(Slot.id == uuid.UUID(slot_id)).values(exam_completed_at=datetime.now(UTC))
    )
    await db_session.flush()


async def test_a_strong_candidate_outranks_a_weak_one(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [await published_station(client, admin, "kings", "S1")]

    strong = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="strong@example.com"
    )
    weak = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="weak@example.com"
    )
    for candidate, rag in ((strong, "G"), (weak, "R")):
        slot_id = candidate["circuit"]["slots"][0]["id"]
        await finish(db_session, slot_id)
        await mark(client, admin, slot_id, rag)

    response = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cohort", headers=bearer(admin))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["cohort_size"] == 2
    by_user = {c["trainee"]["user_id"]: c for c in body["candidates"]}
    assert by_user[strong["user_id"]]["assessment_score"] == 100.0
    assert by_user[weak["user_id"]]["assessment_score"] == 33.0
    assert by_user[strong["user_id"]]["rank"] < by_user[weak["user_id"]]["rank"]
    assert [c["rank"] for c in body["candidates"]] == [1, 2]


async def test_completion_ranks_before_average_score(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The rule worth porting.

    A perfect score on half the stations ranks *below* a worse score on all of
    them: the unfinished examination is the thing nobody has looked at.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [
        await published_station(client, admin, "kings", "S1"),
        await published_station(client, admin, "kings", "S2"),
    ]

    finisher = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="finisher@example.com"
    )
    quitter = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="quitter@example.com"
    )

    # Finished both, scored amber throughout.
    for slot in finisher["circuit"]["slots"]:
        await finish(db_session, slot["id"])
        await mark(client, admin, slot["id"], "A")
    # Sat one of two, and scored top marks on it.
    await finish(db_session, quitter["circuit"]["slots"][0]["id"])
    await mark(client, admin, quitter["circuit"]["slots"][0]["id"], "G")

    body = (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cohort", headers=bearer(admin))
    ).json()
    by_user = {c["trainee"]["user_id"]: c for c in body["candidates"]}

    assert by_user[quitter["user_id"]]["assessment_score"] == 100.0
    assert by_user[finisher["user_id"]]["assessment_score"] == 66.0
    # Higher score, lower rank.
    assert by_user[finisher["user_id"]]["rank"] < by_user[quitter["user_id"]]["rank"]

    assert by_user[finisher["user_id"]]["completion_rate"] == 1.0
    assert by_user[quitter["user_id"]]["completion_rate"] == 0.5
    assert by_user[quitter["user_id"]]["review_priority"] == "high"
    assert by_user[finisher["user_id"]]["review_priority"] == "standard"


async def test_a_candidate_who_sat_almost_nothing_is_urgent(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Under half the stations, whatever they scored on the ones they sat."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [
        await published_station(client, admin, "kings", "S1"),
        await published_station(client, admin, "kings", "S2"),
        await published_station(client, admin, "kings", "S3"),
    ]
    candidate = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="absent@example.com"
    )
    slot_id = candidate["circuit"]["slots"][0]["id"]
    await finish(db_session, slot_id)
    await mark(client, admin, slot_id, "G")

    body = (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cohort", headers=bearer(admin))
    ).json()
    row = body["candidates"][0]
    assert row["stations_completed"] == 1
    assert row["stations_total"] == 3
    assert row["assessment_score"] == 100.0
    assert row["review_priority"] == "urgent"


async def test_an_unmarked_candidate_has_no_score_rather_than_a_zero(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A zero would rank somebody nobody has marked below somebody who failed."""
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [await published_station(client, admin, "kings", "S1")]
    candidate = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="unmarked@example.com"
    )
    await finish(db_session, candidate["circuit"]["slots"][0]["id"])

    body = (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cohort", headers=bearer(admin))
    ).json()
    row = body["candidates"][0]
    assert row["assessment_score"] is None
    assert row["completion_rate"] == 1.0
    # A finished examination with no automatic score has nothing to rank on.
    assert row["review_priority"] == "standard"


async def test_a_training_sitting_has_no_cohort(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Oracle: `test_cohort_summary_rejects_training_session`.

    Training is people practising. Ranking them against each other would turn
    practice into an assessment nobody agreed to sit.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")

    response = await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cohort", headers=bearer(admin))
    assert response.status_code == 422
    assert response.json()["code"] == "not_an_exam_sitting"


async def test_a_sitting_with_nobody_in_it_is_an_empty_cohort(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")

    body = (
        await client.get(f"/api/v1/orgs/kings/sittings/{sitting['id']}/cohort", headers=bearer(admin))
    ).json()
    assert body["cohort_size"] == 0
    assert body["candidates"] == []


async def test_another_organisations_cohort_is_not_readable(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    _, other_admin = await org_with_admin(client, make_actor, slug="guys")
    sitting = await a_sitting(client, admin, "kings")

    response = await client.get(
        f"/api/v1/orgs/guys/sittings/{sitting['id']}/cohort", headers=bearer(other_admin)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "sitting_not_found"
