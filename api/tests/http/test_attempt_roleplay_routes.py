"""The actor script is available only after an owned consultation."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, repository
from tests.http.test_attempt_material_routes import NOW, _entitled_attempt
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def test_roleplay_is_private_and_post_consultation(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,
) -> None:
    token = await make_actor("roleplay-owner@example.com")
    other = await make_actor("roleplay-other@example.com")
    sat = await _entitled_attempt(db_session, "roleplay-owner@example.com")
    url = f"/api/v1/attempts/{sat.attempt_id}/roleplay"
    assert (await client.get(url, headers=bearer(other))).status_code == 403
    assert (await client.get(url, headers=bearer(token))).status_code == 409
    await repository.set_status(db_session, sat.attempt_id, status=domain.Status.RUNNING, at=NOW)
    assert (await client.get(url, headers=bearer(token))).status_code == 409
    await repository.set_status(db_session, sat.attempt_id, status=domain.Status.INTERACTION_COMPLETE, at=NOW)
    await db_session.commit()
    response = await client.get(url, headers=bearer(token))
    assert response.status_code == 200, response.text
    body = response.json()
    section_ids = {section["id"] for section in body["sections"]}
    assert section_ids == {"patient_information"}
    patient = next(s for s in body["sections"] if s["id"] == "patient_information")
    blocks = {block["id"]: block["value"] for block in patient["blocks"]}
    assert blocks["opening_sentence"] == "Doctor, I have this pain."
    assert blocks["expanded_history"] == "Crushing central chest pain for three days."
    assert blocks["persona"] == "Anxious, talks quickly"
    assert "management_plan" not in section_ids


async def test_standalone_debrief_requires_owned_finished_recording(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,
) -> None:
    token = await make_actor("debrief-owner@example.com")
    other = await make_actor("debrief-other@example.com")
    sat = await _entitled_attempt(db_session, "debrief-owner@example.com")
    url = f"/api/v1/attempts/{sat.attempt_id}/debriefs"
    assert (await client.post(url, headers=bearer(other))).status_code == 403
    early = await client.post(url, headers=bearer(token))
    assert early.status_code == 409
    assert early.json()["code"] == "attempt_not_finished"
    await repository.set_status(db_session, sat.attempt_id, status=domain.Status.FAILED, at=NOW)
    await db_session.commit()
    empty = await client.post(url, headers=bearer(token))
    assert empty.status_code == 409
    assert empty.json()["code"] == "attempt_not_ready"
