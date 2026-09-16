"""Reviewing a slot, and not overwriting someone else's work."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def org_with_admin(client: AsyncClient, make_actor, slug: str = "kings"):  # type: ignore[no-untyped-def]
    root = await make_actor(f"root-{slug}@osceguide.com", platform_admin=True)
    created = await client.post(
        "/api/v1/platform/organizations",
        json={"slug": slug, "name": slug.title(), "org_type": "institution"},
        headers=bearer(root),
    )
    org_id = uuid.UUID(created.json()["id"])
    admin = await make_actor(
        f"admin-{slug}@example.com",
        memberships=(Membership(org_id=org_id, org_slug=slug, role="owner"),),
        active_org_slug=slug,
    )
    return org_id, admin


async def a_slot(db_session: AsyncSession, org_id: uuid.UUID) -> uuid.UUID:
    """A slot, built directly: reviewing does not care how it was scheduled."""
    from app.features.catalog import repository as catalog_repo
    from app.features.identity import repository as identity_repo
    from app.features.sittings.models import Circuit, Sitting, Slot
    from app.features.stations.models import (
        FeedbackTemplate,
        FeedbackTemplateVersion,
        Station,
        StationVersion,
    )

    exam = await catalog_repo.exam_by_code(db_session, "sca")
    assert exam is not None

    template = FeedbackTemplate(org_id=org_id, title="R")
    db_session.add(template)
    await db_session.flush()
    template_version = FeedbackTemplateVersion(
        org_id=org_id, template_id=template.id, version=1, field_selection={}, status="published"
    )
    station = Station(owner_kind="org", org_id=org_id, exam_id=exam.id, title="S")
    db_session.add_all([template_version, station])
    await db_session.flush()
    station_version = StationVersion(
        station_id=station.id, org_id=org_id, version=1, content={}, status="published"
    )
    db_session.add(station_version)
    await db_session.flush()

    sitting = Sitting(
        org_id=org_id,
        name="S",
        mode="exam",
        feedback_template_version_id=template_version.id,
    )
    db_session.add(sitting)
    await db_session.flush()
    circuit = Circuit(org_id=org_id, sitting_id=sitting.id, name="C")
    db_session.add(circuit)
    await db_session.flush()
    trainee = await identity_repo.create_user(
        session=db_session, email=f"t{uuid.uuid4().hex[:8]}@example.com", name="T", password_hash=None
    )
    slot = Slot(
        org_id=org_id,
        circuit_id=circuit.id,
        slot_index=0,
        trainee_id=trainee.id,
        station_version_id=station_version.id,
    )
    db_session.add(slot)
    await db_session.flush()
    return slot.id


async def test_a_review_is_saved_and_listed(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)

    saved = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"communication.score": "g"}, "notes": "Clear"},
        headers=bearer(admin),
    )
    assert saved.status_code == 200
    assert saved.json()["field_values"]["communication.score"] == "G"

    listed = await client.get(f"/api/v1/orgs/kings/slots/{slot_id}/reviews", headers=bearer(admin))
    assert len(listed.json()["items"]) == 1


async def test_submitting_twice_edits_rather_than_duplicates(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"

    await client.put(url, json={"notes": "First"}, headers=bearer(admin))
    await client.put(url, json={"notes": "Second"}, headers=bearer(admin))

    listed = await client.get(f"/api/v1/orgs/kings/slots/{slot_id}/reviews", headers=bearer(admin))
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["notes"] == "Second"


async def test_an_invalid_rating_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    response = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"communication.score": "X"}},
        headers=bearer(admin),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_rag"


async def test_a_gp_lead_review_is_revisioned(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    url = f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review"

    first = await client.put(url, json={"revision": 0, "notes": "One"}, headers=bearer(admin))
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    second = await client.put(url, json={"revision": 1, "notes": "Two"}, headers=bearer(admin))
    assert second.json()["revision"] == 2


async def test_a_stale_revision_is_refused(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    """Two reviewers with the screen open. b2b's client detects this by matching
    the words "another user" in an error string."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    url = f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review"

    await client.put(url, json={"revision": 0, "notes": "One"}, headers=bearer(admin))
    stale = await client.put(url, json={"revision": 0, "notes": "Clobber"}, headers=bearer(admin))
    assert stale.status_code == 409
    assert stale.json()["code"] == "review_conflict"

    current = await client.get(url, headers=bearer(admin))
    assert current.json()["notes"] == "One"


async def test_a_supervisor_may_not_write_a_gp_lead_review(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Institution admin only — the narrower role that also signs off results."""
    org_id, _ = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    supervisor = await make_actor(
        "sup@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    response = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review",
        json={"revision": 0},
        headers=bearer(supervisor),
    )
    assert response.status_code == 403


async def test_another_orgs_slot_reviews_are_invisible(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    kings_id, kings_admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    slot_id = await a_slot(db_session, kings_id)
    await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"notes": "Private"},
        headers=bearer(kings_admin),
    )
    response = await client.get(f"/api/v1/orgs/guys/slots/{slot_id}/reviews", headers=bearer(guys_admin))
    assert response.json()["items"] == []
