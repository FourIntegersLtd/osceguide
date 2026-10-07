"""Reviewing a slot, and not overwriting someone else's work."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from tests.support.catalog import create_exam, ensure_exam
from tests.support.rubrics import published_feedback_version, rubric_with_domains
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
    # Nothing is seeded, so the exam an org's stations name has to be written
    # first — by a platform admin, which is exactly who is holding this token.
    await create_exam(client, root, code="sca")
    return org_id, admin


async def a_slot(
    db_session: AsyncSession, org_id: uuid.UUID, domains: tuple[str, ...] = ("communication",)
) -> uuid.UUID:
    """A slot, built directly: reviewing does not care how it was scheduled.

    `domains` is what the sitting's rubric asks reviewers to score (R-1).
    """
    from app.features.identity import repository as identity_repo
    from app.features.sittings.models import Circuit, Sitting, Slot
    from app.features.stations.models import (
        Station,
        StationVersion,
    )

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None

    # A template narrows a rubric, and the selection is checked against that
    # rubric's own domains — so the rubric has to have the ones under test.
    template_version = await published_feedback_version(
        db_session,
        org_id,
        structure=rubric_with_domains(*domains),
    )
    station = Station(owner_kind="org", org_id=org_id, exam_id=exam.id, title="S")
    db_session.add(station)
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
        rubric_version_id=template_version.id,
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
    # Committed (releasing the test's savepoint) rather than flushed: a request
    # the API refuses rolls the session back, and a flushed arrangement would
    # go with it. The fixture's outer transaction still discards everything.
    await db_session.commit()
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
    assert response.json()["code"] == "invalid_rating"


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


async def test_an_org_cannot_write_a_review_against_another_orgs_slot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The write side of the isolation, which nothing checked.

    `test_another_orgs_slot_reviews_are_invisible` asserts only that the read
    comes back empty — and it does, because reads filter on `org_id`. The write
    took `org_id` from the path slug and the slot id from the URL and never
    compared them, so an admin of any org could attach a review to any slot in
    the system. It stayed invisible to the slot's real owner, which is what
    made it look contained.
    """
    from sqlalchemy import func, select

    from app.features.reviews.models import SlotReview

    kings_id, _ = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    kings_slot = await a_slot(db_session, kings_id)

    response = await client.put(
        f"/api/v1/orgs/guys/slots/{kings_slot}/reviews/mine",
        json={"field_values": {"communication.score": "r"}, "notes": "Not mine to write"},
        headers=bearer(guys_admin),
    )

    assert response.status_code == 404, response.text
    assert response.json()["code"] == "slot_not_found"
    written = await db_session.scalar(
        select(func.count()).select_from(SlotReview).where(SlotReview.slot_id == kings_slot)
    )
    assert written == 0, "a review was stored against another org's slot"


async def test_an_org_cannot_write_a_gp_lead_review_against_another_orgs_slot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    kings_id, _ = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    kings_slot = await a_slot(db_session, kings_id)

    response = await client.put(
        f"/api/v1/orgs/guys/slots/{kings_slot}/gp-lead-review",
        json={"revision": 0},
        headers=bearer(guys_admin),
    )

    assert response.status_code == 404, response.text


async def test_a_review_completes_once_every_domain_is_scored(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-1, wired. The router used to pass an empty required set, which
    `ensure_completable` refuses outright — no review could ever be completed."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id, domains=("communication", "data_gathering"))
    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"

    partial = await client.put(
        url,
        json={"field_values": {"communication.score": "G"}, "status": "completed"},
        headers=bearer(admin),
    )
    assert partial.status_code == 409, partial.text
    assert partial.json()["code"] == "review_incomplete"
    # B55: the rubric's own title, never the id a reader would have to decode.
    assert (
        partial.json()["message"]
        == "Score every domain before completing the review; still missing: Data Gathering"
    )

    complete = await client.put(
        url,
        json={
            "field_values": {"communication.score": "G", "data_gathering.score": "A"},
            "status": "completed",
        },
        headers=bearer(admin),
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "completed"
    assert complete.json()["completed_at"] is not None


async def test_a_rubric_with_nothing_to_score_cannot_be_completed(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id, domains=())
    response = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {}, "status": "completed"},
        headers=bearer(admin),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "nothing_to_review"


async def test_a_gp_lead_review_needs_every_domain_too(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, _ = await org_with_admin(client, make_actor)
    lead = await make_actor(
        "lead-kings@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="institution_admin"),),
        active_org_slug="kings",
    )
    slot_id = await a_slot(db_session, org_id, domains=("communication",))
    url = f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review"

    partial = await client.put(
        url, json={"revision": 0, "field_values": {}, "status": "completed"}, headers=bearer(lead)
    )
    assert partial.status_code == 409, partial.text
    assert partial.json()["code"] == "review_incomplete"
    assert (
        partial.json()["message"]
        == "Score every domain before completing the review; still missing: Communication"
    )

    complete = await client.put(
        url,
        json={"revision": 0, "field_values": {"communication.score": "R"}, "status": "completed"},
        headers=bearer(lead),
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] == "completed"


async def test_two_reviewers_who_disagree_are_combined_worst_first(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """b2b's tie-break, moved off the browser.

    `combine_rag` was written, unit-tested, documented and called by nothing,
    so the console, a released result and an export could each work out a
    candidate's rating differently.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id, domains=("communication", "management"))
    second = await make_actor(
        "observer@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )

    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"
    await client.put(
        url,
        json={
            "field_values": {"communication.score": "G", "management.score": "G"},
            "status": "completed",
        },
        headers=bearer(admin),
    )
    await client.put(
        url,
        json={
            "field_values": {"communication.score": "A", "management.score": "G"},
            "status": "completed",
        },
        headers=bearer(second),
    )

    listed = await client.get(f"/api/v1/orgs/kings/slots/{slot_id}/reviews", headers=bearer(admin))
    summary = listed.json()["summary"]
    assert summary["completed_reviews"] == 2
    # The lower rating wins: it is the one that should prompt a conversation.
    assert summary["by_domain"] == {"communication": "A", "management": "G"}
    assert summary["overall_rag"] == "A"
    # R-2: a reader is never left to humanise a domain id itself.
    assert summary["domain_labels"] == {"communication": "Communication", "management": "Management"}


async def test_a_draft_review_does_not_count_towards_the_summary(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """Somebody part-way through marking has not said anything yet."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)

    await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"communication.score": "R"}, "status": "draft"},
        headers=bearer(admin),
    )

    summary = (await client.get(f"/api/v1/orgs/kings/slots/{slot_id}/reviews", headers=bearer(admin))).json()[
        "summary"
    ]
    assert summary["completed_reviews"] == 0
    assert summary["overall_rag"] is None
    assert summary["by_domain"] == {}


async def test_a_slot_nobody_has_reviewed_still_has_a_summary(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """A shape the console can render, not a 404 and not a missing key."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)

    body = (await client.get(f"/api/v1/orgs/kings/slots/{slot_id}/reviews", headers=bearer(admin))).json()
    assert body["items"] == []
    assert body["summary"]["slot_id"] == str(slot_id)
    assert body["summary"]["overall_rag"] is None


async def test_an_examiner_reads_back_only_their_own_review(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A draft is picked up where it was left, and nobody else's is returned."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    colleague = await make_actor(
        "colleague-kings@example.com",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="owner"),),
        active_org_slug="kings",
    )
    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"
    await client.put(url, json={"notes": "Mine"}, headers=bearer(admin))
    await client.put(url, json={"notes": "Theirs"}, headers=bearer(colleague))

    mine = await client.get(url, headers=bearer(admin))
    assert mine.status_code == 200, mine.text
    assert mine.json()["notes"] == "Mine"
    assert mine.json()["status"] == "draft"


async def test_reads_before_any_review_exists_answer_null_not_404(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """B51: no review yet is an ordinary state, so the console logs no 404 for it."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    for path in (f"slots/{slot_id}/reviews/mine", f"slots/{slot_id}/gp-lead-review"):
        missing = await client.get(f"/api/v1/orgs/kings/{path}", headers=bearer(admin))
        assert missing.status_code == 200, missing.text
        assert missing.json() is None
    # A slot that does not exist is still a wrong id, not an empty answer.
    wrong = await client.get(f"/api/v1/orgs/kings/slots/{uuid.uuid4()}/reviews/mine", headers=bearer(admin))
    assert wrong.status_code == 404
    assert wrong.json()["code"] == "slot_not_found"


async def test_my_review_of_another_orgs_slot_cannot_be_read(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    kings_id, _ = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    kings_slot = await a_slot(db_session, kings_id)
    refused = await client.get(
        f"/api/v1/orgs/guys/slots/{kings_slot}/reviews/mine", headers=bearer(guys_admin)
    )
    assert refused.status_code == 404, refused.text
    assert refused.json()["code"] == "slot_not_found"


async def _circuit_of(db_session: AsyncSession, slot_id: uuid.UUID) -> uuid.UUID:
    """The circuit a fixture slot was built in."""
    from sqlalchemy import select

    from app.features.sittings.models import Slot

    circuit_id = await db_session.scalar(select(Slot.circuit_id).where(Slot.id == slot_id))
    assert circuit_id is not None
    return circuit_id


async def test_whether_a_circuit_review_was_published_can_be_read(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Null until finalised; then who finalised it and when."""
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id = await _circuit_of(db_session, await a_slot(db_session, org_id))
    url = f"/api/v1/orgs/kings/circuits/{circuit_id}/review"

    finalized = await client.post(f"{url}/finalize", json={"merged_notes": "Good day"}, headers=bearer(admin))
    assert finalized.status_code == 200, finalized.text

    read = await client.get(url, headers=bearer(admin))
    assert read.status_code == 200, read.text
    assert read.json()["merged_notes"] == "Good day"
    assert read.json()["finalized_at"] == finalized.json()["finalized_at"]
    assert read.json()["finalized_by"] is not None
    assert read.json()["finalized_by"] == finalized.json()["finalized_by"]


async def test_a_circuit_review_reads_as_null_until_it_is_published(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id = await _circuit_of(db_session, await a_slot(db_session, org_id))
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    await client.post(
        f"/api/v1/orgs/kings/circuits/{circuit_id}/review/finalize", json={}, headers=bearer(admin)
    )

    unpublished = await client.get(
        f"/api/v1/orgs/guys/circuits/{circuit_id}/review", headers=bearer(guys_admin)
    )
    assert unpublished.status_code == 200, unpublished.text
    assert unpublished.json() is None


async def test_a_signed_off_result_locks_the_reviews_behind_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-4: a GP lead could rewrite a review after the decision built on it was signed off."""
    from sqlalchemy import select

    from app.features.roster import repository as roster_repo
    from app.features.sittings.models import Circuit, Slot
    from tests.http.test_results_routes import EVIDENCE

    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    slot = (await db_session.execute(select(Slot).where(Slot.id == slot_id))).scalar_one()
    user_id = slot.trainee_id
    sitting_id = (
        await db_session.execute(select(Circuit.sitting_id).where(Circuit.id == slot.circuit_id))
    ).scalar_one()
    trainee = await roster_repo.create_trainee(
        db_session,
        org_id,
        email=f"r4-{uuid.uuid4().hex[:6]}@example.com",
        first_name="T",
        last_name=None,
        cohort_id=None,
    )
    trainee_id = trainee.id
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee_id, user_id=user_id)
    await db_session.commit()

    review = f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review"
    saved = await client.put(review, json={"revision": 0, "notes": "Before"}, headers=bearer(admin))
    assert saved.status_code == 200, saved.text
    decision = f"/api/v1/orgs/kings/sittings/{sitting_id}/candidates/{trainee_id}/decision"
    drafted = await client.put(
        decision,
        json={
            "assessment_outcome": "pass",
            "rationale": "Met it.",
            "evidence": EVIDENCE,
            "expected_revision": 0,
        },
        headers=bearer(admin),
    )
    assert drafted.status_code == 200, drafted.text
    signed = await client.post(f"{decision}/sign-off", headers=bearer(admin))
    assert signed.status_code == 200, signed.text

    response = await client.put(review, json={"revision": 1, "notes": "After"}, headers=bearer(admin))

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "review_locked"
    stored = await client.get(review, headers=bearer(admin))
    assert stored.json()["notes"] == "Before"
