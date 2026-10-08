"""Only someone who may run circuits can lead one (R-38)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.http.test_examiner_transcript_routes import an_examiner
from tests.http.test_sittings_routes import a_template_version, a_trainee, published_station
from tests.support.sittings import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _sitting_and_station(client: AsyncClient, admin: str) -> tuple[str, str]:
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "Finals", "programme_id": str(template), "mode": "exam"},
            headers=bearer(admin),
        )
    ).json()
    return sitting["id"], await published_station(client, admin, "kings", "Sore knee")


async def test_a_trainee_cannot_lead_a_circuit_but_a_supervisor_can(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    sitting_id, station = await _sitting_and_station(client, admin)
    candidate = await a_trainee(db_session, "cand@example.com")
    lead = await a_trainee(db_session, "lead@example.com")
    supervisor, _ = await an_examiner(db_session, org_id, "sup@example.com")

    def body(leader: object) -> dict[str, object]:
        return {
            "name": "Room 1",
            "trainee_ids": [str(candidate)],
            "station_version_ids": [station],
            "supervisor_user_id": str(leader),
        }

    url = f"/api/v1/orgs/kings/sittings/{sitting_id}/circuits"
    accepted = await client.post(url, json=body(supervisor), headers=bearer(admin))
    assert accepted.status_code == 201, accepted.text

    circuit_id = accepted.json()["id"]
    edit = await client.put(
        f"/api/v1/orgs/kings/circuits/{circuit_id}",
        json={**body(lead), "timing": {}},
        headers=bearer(admin),
    )
    assert (edit.status_code, edit.json()["code"]) == (409, "lead_cannot_run")

    refused = await client.post(url, json=body(lead), headers=bearer(admin))
    assert (refused.status_code, refused.json()["code"]) == (409, "lead_cannot_run")
