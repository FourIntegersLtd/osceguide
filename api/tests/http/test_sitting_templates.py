"""Exam templates: saved by an org admin, scoped to their org, listed, renamed and deleted."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.http.test_results_routes import org_with_admin
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

BASE = "/api/v1/orgs/kings/sitting-templates"


def _body(name: str = "Summer OSCE") -> dict:  # type: ignore[type-arg]
    return {
        "name": name,
        "config": {
            "mode": "exam",
            "stations": [{"version_id": str(uuid.uuid4()), "title": "Chest pain"}],
            "reading_minutes": 2,
            "consultation_minutes": 8,
            "break_minutes": 3,
            "breaks": [{"after": 1, "minutes": 7}],
            "assessor_style": "per_candidate",
        },
    }


async def test_a_template_is_saved_listed_renamed_and_deleted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _org, admin = await org_with_admin(client, make_actor)
    made = await client.post(BASE, json=_body(), headers=bearer(admin))
    assert made.status_code == 201, made.text
    assert made.json()["config"]["assessor_style"] == "per_candidate"
    template_id = made.json()["id"]

    clash = await client.post(BASE, json=_body("summer osce"), headers=bearer(admin))
    assert clash.status_code == 409
    assert clash.json()["code"] == "template_name_taken"

    listed = await client.get(BASE, headers=bearer(admin))
    assert [row["name"] for row in listed.json()] == ["Summer OSCE"]

    renamed = await client.put(f"{BASE}/{template_id}", json={"name": " Winter OSCE "}, headers=bearer(admin))
    assert renamed.json()["name"] == "Winter OSCE"

    assert (await client.delete(f"{BASE}/{template_id}", headers=bearer(admin))).status_code == 204
    gone = await client.delete(f"{BASE}/{template_id}", headers=bearer(admin))
    assert gone.json()["code"] == "template_not_found"


async def test_a_template_is_invisible_to_another_org_and_to_a_supervisor(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    template_id = (await client.post(BASE, json=_body(), headers=bearer(admin))).json()["id"]

    _other_id, other_admin = await org_with_admin(client, make_actor, slug="rival")
    assert (
        await client.get("/api/v1/orgs/rival/sitting-templates", headers=bearer(other_admin))
    ).json() == []
    stolen = await client.delete(
        f"/api/v1/orgs/rival/sitting-templates/{template_id}", headers=bearer(other_admin)
    )
    assert stolen.status_code == 404
    cross = await client.get(BASE, headers=bearer(other_admin))
    assert cross.status_code == 403

    supervisor = await make_actor(
        "sup-tpl@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    assert (await client.get(BASE, headers=bearer(supervisor))).status_code == 403
    assert (await client.post(BASE, json=_body("Other"), headers=bearer(supervisor))).status_code == 403
    assert len((await client.get(BASE, headers=bearer(admin))).json()) == 1


async def test_a_template_with_an_unknown_mode_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _org, admin = await org_with_admin(client, make_actor)
    body = _body()
    body["config"]["mode"] = "party"
    assert (await client.post(BASE, json=body, headers=bearer(admin))).status_code == 422
