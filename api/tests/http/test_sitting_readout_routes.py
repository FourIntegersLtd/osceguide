"""The cohort read-out: the document an institution downloads after an examination.

Oracle: `b2b-api/app/features/sessions/cohort_report.py::build_readout` behind
`GET /orgs/{org}/sessions/{id}/readout`, and the "Export readout" button in
`frontend/src/b2b/components/features/sessions/SessionCohortReportSection.tsx`
and `OrgSessionsPage.tsx`. The legacy route answered JSON by default and rendered
a markdown attachment when asked for one; only the document is ported — the
screen writes the file — so what is asserted here is that the document says what
the legacy one said: who completed, what the cohort averaged, who needs looking
at, and how the numbers were arrived at.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_cohort_summary_routes import a_candidate, finish, mark
from tests.http.test_org_read_models import a_sitting
from tests.http.test_sittings_routes import org_with_admin, published_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def read(client: AsyncClient, token: str, sitting_id: str):  # type: ignore[no-untyped-def]
    return await client.get(f"/api/v1/orgs/kings/sittings/{sitting_id}/readout", headers=bearer(token))


async def test_a_cohort_is_summed_and_ranked_in_one_document(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The three things the legacy read-out led with, from one sitting."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [
        await published_station(client, admin, "kings", "S1"),
        await published_station(client, admin, "kings", "S2"),
    ]
    strong = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="strong@example.com"
    )
    weak = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="weak@example.com"
    )
    for candidate, rag in ((strong, "G"), (weak, "R")):
        for slot in candidate["circuit"]["slots"]:
            await finish(db_session, slot["id"])
            await mark(client, admin, slot["id"], rag)

    response = await read(client, admin, sitting["id"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["org_slug"] == "kings"
    assert body["sitting"]["name"] == "Finals"
    assert body["sitting"]["required_station_count"] == 2
    summary = body["summary"]
    assert summary["cohort_size"] == 2
    assert summary["fully_complete_count"] == 2, "both sat both stations"
    assert summary["average_assessment_score"] == 66.5, "(100 + 33) / 2"
    # A full completion at 100 is `low` priority — streamlined sign-off — and a full
    # completion at 33 is `high`. All four bands are always counted, so two
    # sittings compared across a term are compared on the same shape.
    assert summary["priorities"] == {"urgent": 0, "high": 1, "standard": 0, "low": 1}
    assert [c["rank"] for c in body["candidates"]] == [1, 2]
    assert body["candidates"][0]["trainee"]["email"] == "strong@example.com"
    assert body["methodology"], "the document has to say how it was worked out"


async def test_the_recommendations_say_who_needs_looking_at(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The legacy `_build_recommendations`, with its bands intact.

    The urgent count outranks the high one in the same sentence set, and the
    closing line is the one the document cannot leave out: it ranks people, and
    it has to say that ranking them is not the decision.
    """
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [await published_station(client, admin, "kings", "S1")]
    half = await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="half@example.com"
    )
    await finish(db_session, half["circuit"]["slots"][0]["id"])

    lines = (await read(client, admin, sitting["id"])).json()["recommendations"]

    assert any("1 of 1 candidates (100%) completed every required station" in line for line in lines)
    assert any("high-priority review" in line for line in lines)
    assert lines[-1].startswith("The final decision rests with the institution's GP lead.")


async def test_an_unmarked_cohort_has_no_average_rather_than_a_zero(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """A document that said 0 would tell a course lead their cohort failed."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    stations = [await published_station(client, admin, "kings", "S1")]
    await a_candidate(
        client, admin, db_session, sitting_id=sitting["id"], stations=stations, email="raw@example.com"
    )

    body = (await read(client, admin, sitting["id"])).json()

    assert body["summary"]["average_assessment_score"] is None
    assert not any("Cohort averages" in line for line in body["recommendations"])


async def test_an_empty_sitting_is_a_document_of_zeroes(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """Not a 404: there is a sitting, and nobody sat it."""
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")

    body = (await read(client, admin, sitting["id"])).json()

    assert body["summary"]["cohort_size"] == 0
    assert body["candidates"] == []
    assert body["recommendations"] == ["No candidates were assigned to this sitting."]


async def test_a_training_sitting_has_no_readout(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """Oracle: `test_cohort_summary_rejects_training_session`.

    b2b answered 400 "Cohort report is only available for exam sessions"; this is
    the platform's own code for a request that cannot mean anything, the same one
    `/cohort` already gives.
    """
    _, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings", mode="training")

    response = await read(client, admin, sitting["id"])

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "not_an_exam_sitting"


async def test_a_supervisor_cannot_read_a_cohort_export(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    """The legacy route was administrator-only, and this document is the export.

    It names every candidate, their score and who has still to be looked at, in
    one payload, and it exists to be printed and circulated. A supervisor running
    one circuit reads their own console; they do not take the cohort.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    sitting = await a_sitting(client, admin, "kings")
    supervisor = await make_actor(
        "sup-readout@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    response = await read(client, supervisor, sitting["id"])

    assert response.status_code == 403, response.text


async def test_another_organisations_readout_does_not_exist(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
) -> None:
    _, admin = await org_with_admin(client, make_actor, "kings")
    _, guys = await org_with_admin(client, make_actor, "guys")
    sitting = await a_sitting(client, admin, "kings")

    response = await client.get(f"/api/v1/orgs/guys/sittings/{sitting['id']}/readout", headers=bearer(guys))

    assert response.status_code == 404, response.text
    assert response.json()["code"] == "sitting_not_found"
