"""Reviewing a slot, and not overwriting someone else's work."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.attempts.domain import SCORING_FAILED
from tests.support.catalog import create_exam, ensure_exam
from tests.support.decisions import settle_decision
from tests.support.rubrics import published_feedback_version, rubric_with_domains
from tests.support.tokens import bearer, mint_token

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
    db_session: AsyncSession,
    org_id: uuid.UUID,
    domains: tuple[str, ...] = ("communication",),
    *,
    mode: str = "exam",
    supervisor: uuid.UUID | None = None,
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
        mode=mode,
        rubric_version_id=template_version.id,
    )
    db_session.add(sitting)
    await db_session.flush()
    circuit = Circuit(org_id=org_id, sitting_id=sitting.id, name="C", supervisor_user_id=supervisor)
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
        # Sat, as a reviewed station is, so a decision may be recorded on it (R-11).
        status="completed",
    )
    db_session.add(slot)
    # Committed (releasing the test's savepoint) rather than flushed: a request
    # the API refuses rolls the session back, and a flushed arrangement would
    # go with it. The fixture's outer transaction still discards everything.
    await db_session.commit()
    return slot.id


async def a_supervisor(db_session: AsyncSession, org_id: uuid.UUID, email: str) -> tuple[uuid.UUID, str]:
    """A real supervisor account and its token; the id is what a circuit names."""
    from app.features.identity import repository as identity_repo
    from app.features.tenancy import repository as tenancy_repo

    user = await identity_repo.create_user(db_session, email=email, name=email, password_hash=None)
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=user.id, role="supervisor")
    await db_session.commit()
    token = mint_token(
        user_id=user.id,
        email=email,
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    return user.id, token


async def a_rostered_candidate(db_session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """Put the slot's candidate on the roster: returns (their users.id, the sitting, their trainees.id)."""
    from sqlalchemy import select

    from app.features.roster import repository as roster_repo
    from app.features.sittings.models import Circuit, Slot

    slot = (await db_session.execute(select(Slot).where(Slot.id == slot_id))).scalar_one()
    user_id = slot.trainee_id
    sitting_id = (
        await db_session.execute(select(Circuit.sitting_id).where(Circuit.id == slot.circuit_id))
    ).scalar_one()
    trainee = await roster_repo.create_trainee(
        db_session,
        org_id,
        email=f"c-{uuid.uuid4().hex[:6]}@example.com",
        first_name="T",
        last_name=None,
        cohort_id=None,
    )
    trainee_id = trainee.id
    await roster_repo.link_trainee_to_user(db_session, org_id, trainee_id, user_id=user_id)
    await db_session.commit()
    return user_id, sitting_id, trainee_id


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
    supervisor_id, second = await a_supervisor(db_session, org_id, "observer@example.com")
    slot_id = await a_slot(
        db_session, org_id, domains=("communication", "management"), supervisor=supervisor_id
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
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    _, sitting_id, trainee_id = await a_rostered_candidate(db_session, org_id, slot_id)

    review = f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review"
    saved = await client.put(
        review,
        json={
            "revision": 0,
            "notes": "Before",
            "field_values": {"communication.score": "G"},
            "status": "completed",
        },
        headers=bearer(admin),
    )
    assert saved.status_code == 200, saved.text
    await settle_decision(client, admin, org_slug="kings", sitting_id=sitting_id, trainee_id=trainee_id)

    response = await client.put(review, json={"revision": 1, "notes": "After"}, headers=bearer(admin))

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "review_locked"
    stored = await client.get(review, headers=bearer(admin))
    assert stored.json()["notes"] == "Before"


async def test_only_the_named_supervisor_or_an_administrator_reviews_a_slot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-9: any supervisor in the organisation could review any slot in it."""
    org_id, _ = await org_with_admin(client, make_actor)
    named_id, named = await a_supervisor(db_session, org_id, "named@example.com")
    _, other = await a_supervisor(db_session, org_id, "other@example.com")
    slot_id = await a_slot(db_session, org_id, supervisor=named_id)
    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"

    refused = await client.put(url, json={"notes": "Not mine"}, headers=bearer(other))
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "not_slot_reviewer"
    allowed = await client.put(url, json={"notes": "Mine"}, headers=bearer(named))
    assert allowed.status_code == 200, allowed.text


async def test_an_observer_must_be_on_the_organisations_roster(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-9: `observer_trainee_id` was stored unchecked, so it could name anybody's trainee."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)

    response = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"notes": "Watched", "observer_trainee_id": str(uuid.uuid4())},
        headers=bearer(admin),
    )

    assert response.status_code == 404, response.text
    assert response.json()["code"] == "trainee_not_found"


async def test_a_circuit_review_is_finalised_once_and_only_in_its_own_organisation(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-10: finalize had no org check, no circuit_not_found, and could be repeated."""
    org_id, admin = await org_with_admin(client, make_actor)
    circuit_id = await _circuit_of(db_session, await a_slot(db_session, org_id))
    _, guys_admin = await org_with_admin(client, make_actor, "guys")

    foreign = await client.post(
        f"/api/v1/orgs/guys/circuits/{circuit_id}/review/finalize", json={}, headers=bearer(guys_admin)
    )
    assert foreign.status_code == 404, foreign.text
    assert foreign.json()["code"] == "circuit_not_found"
    url = f"/api/v1/orgs/kings/circuits/{circuit_id}/review/finalize"
    first = await client.post(url, json={"merged_notes": "First"}, headers=bearer(admin))
    assert first.status_code == 200, first.text
    second = await client.post(url, json={"merged_notes": "Second"}, headers=bearer(admin))
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "circuit_review_finalized"


async def test_a_circuit_review_cannot_be_finalised_after_sign_off(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-10: notes finalised after the decision was signed off were never part of it."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    _, sitting_id, trainee_id = await a_rostered_candidate(db_session, org_id, slot_id)
    await settle_decision(client, admin, org_slug="kings", sitting_id=sitting_id, trainee_id=trainee_id)

    response = await client.post(
        f"/api/v1/orgs/kings/circuits/{await _circuit_of(db_session, slot_id)}/review/finalize",
        json={"merged_notes": "Late"},
        headers=bearer(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "review_locked"


async def test_a_training_review_is_shared_with_the_trainee_once_completed(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-36: practice has no sign-off or release; the trainee reads a completed review at once."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id, mode="training")
    user_id, _, _ = await a_rostered_candidate(db_session, org_id, slot_id)
    as_trainee = bearer(mint_token(user_id=user_id, email="trainee@example.com"))
    url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"

    await client.put(
        url, json={"field_values": {"communication.score": "G"}, "notes": "Draft"}, headers=bearer(admin)
    )
    waiting = await client.get(f"/api/v1/me/slots/{slot_id}/review", headers=as_trainee)
    assert waiting.json() == {"slot_id": str(slot_id), "state": "not_marked"}
    await client.put(
        url,
        json={"field_values": {"communication.score": "G"}, "notes": "Good rapport", "status": "completed"},
        headers=bearer(admin),
    )

    shared = await client.get(f"/api/v1/me/slots/{slot_id}/review", headers=as_trainee)
    assert shared.status_code == 200, shared.text
    assert shared.json()["state"] == "ready"
    assert shared.json()["notes"] == "Good rapport"
    assert shared.json()["summary"]["overall_rag"] == "G"


async def a_slot_attempt_marking_failed(
    db_session: AsyncSession, org_id: uuid.UUID, slot_id: uuid.UUID, *, frozen: bool = True
) -> uuid.UUID:
    """The candidate's finished attempt on a slot, with the scorer having given up on it."""
    from sqlalchemy import select

    from app.features.attempts import repository as attempts_repo
    from app.features.sittings.models import Slot
    from tests.support.rubrics import frozen_definition

    slot = (await db_session.execute(select(Slot).where(Slot.id == slot_id))).scalar_one()
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    attempt = await attempts_repo.create_attempt(
        db_session,
        kind="exam_slot",
        user_id=slot.trainee_id,
        exam_id=exam.id,
        org_id=org_id,
        station_version_id=slot.station_version_id,
        slot_id=slot_id,
    )
    attempt_id = attempt.id
    now = datetime.now(UTC)
    if frozen:
        await attempts_repo.freeze_definition(
            db_session, attempt_id, definition=frozen_definition(str(attempt_id)), at=now
        )
    await attempts_repo.set_status(db_session, attempt_id, status="running", at=now)
    await attempts_repo.set_status(db_session, attempt_id, status="interaction_complete", at=now)
    await attempts_repo.set_scoring_failure(db_session, attempt_id, reason=SCORING_FAILED)
    await db_session.commit()
    return attempt_id


async def test_staff_see_that_marking_failed_and_can_retry_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-5: the slot's marking says it failed, and a reviewer queues it again from the org."""
    from app.features.attempts import repository as attempts_repo

    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    attempt_id = await a_slot_attempt_marking_failed(db_session, org_id, slot_id)

    feedback = await client.get(f"/api/v1/attempts/{attempt_id}/feedback", headers=bearer(admin))
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["marking_failed"] is True

    retried = await client.post(
        f"/api/v1/orgs/kings/slots/{slot_id}/marking/retry", json={}, headers=bearer(admin)
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["queued"] is True

    attempt = await attempts_repo.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    await db_session.refresh(attempt)
    assert (attempt.status, attempt.failed_reason) == ("interaction_complete", None)
    again = await client.get(f"/api/v1/attempts/{attempt_id}/feedback", headers=bearer(admin))
    assert again.json()["marking_failed"] is False


async def test_marking_cannot_be_retried_when_there_is_no_rubric_to_mark_against(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.attempts import repository as attempts_repo

    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    attempt_id = await a_slot_attempt_marking_failed(db_session, org_id, slot_id, frozen=False)

    refused = await client.post(
        f"/api/v1/orgs/kings/slots/{slot_id}/marking/retry", json={}, headers=bearer(admin)
    )

    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "invalid_attempt_state"
    attempt = await attempts_repo.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    await db_session.refresh(attempt)
    assert attempt.status == "interaction_complete", "the slot is not freed by a retry"


async def test_marking_cannot_be_retried_from_another_organisation(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, _admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    await a_slot_attempt_marking_failed(db_session, org_id, slot_id)
    other_org, other_admin = await org_with_admin(client, make_actor, slug="elsewhere")
    _ = other_org

    refused = await client.post(
        f"/api/v1/orgs/elsewhere/slots/{slot_id}/marking/retry", json={}, headers=bearer(other_admin)
    )
    assert refused.status_code == 404
    assert refused.json()["code"] == "slot_not_found"


async def test_an_exam_review_says_whether_it_waits_for_release_or_for_marking(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """T-8: the candidate is told "not released yet" apart from "not marked yet"."""
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    user_id, sitting_id, trainee_id = await a_rostered_candidate(db_session, org_id, slot_id)
    as_trainee = bearer(mint_token(user_id=user_id, email="trainee@example.com"))
    mine = f"/api/v1/me/slots/{slot_id}/review"

    first = await client.get(mine, headers=as_trainee)
    assert first.json() == {"slot_id": str(slot_id), "state": "not_released"}

    await settle_decision(
        client, admin, org_slug="kings", sitting_id=sitting_id, trainee_id=trainee_id, release=True
    )
    released = await client.get(mine, headers=as_trainee)
    assert released.json() == {"slot_id": str(slot_id), "state": "not_marked"}


async def test_a_draft_review_is_withdrawn_by_its_author_or_the_named_supervisor_only(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """R-44: a stale draft blocked sign-off with nobody able to remove it."""
    org_id, admin = await org_with_admin(client, make_actor)
    named_id, named = await a_supervisor(db_session, org_id, "named-w@example.com")
    _, other = await a_supervisor(db_session, org_id, "other-w@example.com")
    slot_id = await a_slot(db_session, org_id, supervisor=named_id)
    mine = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine"

    drafted = await client.put(mine, json={"notes": "half", "status": "draft"}, headers=bearer(named))
    review_url = f"/api/v1/orgs/kings/slots/{slot_id}/reviews/{drafted.json()['id']}"

    refused = await client.delete(review_url, headers=bearer(other))
    assert (refused.status_code, refused.json()["code"]) == (403, "not_slot_reviewer")
    withdrawn = await client.delete(review_url, headers=bearer(named))
    assert withdrawn.status_code == 204, withdrawn.text
    assert (await client.get(mine, headers=bearer(named))).json() is None

    # An administrator may withdraw a supervisor's draft; nobody withdraws a completed review.
    again = await client.put(mine, json={"notes": "half", "status": "draft"}, headers=bearer(named))
    by_admin = await client.delete(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/{again.json()['id']}", headers=bearer(admin)
    )
    assert by_admin.status_code == 204, by_admin.text
    gone = await client.delete(review_url, headers=bearer(admin))
    assert (gone.status_code, gone.json()["code"]) == (404, "review_not_found")


async def test_a_completed_review_cannot_be_withdrawn(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id, domains=("communication",))
    done = await client.put(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/mine",
        json={"field_values": {"communication.score": "G"}, "status": "completed"},
        headers=bearer(admin),
    )
    assert done.status_code == 200, done.text
    refused = await client.delete(
        f"/api/v1/orgs/kings/slots/{slot_id}/reviews/{done.json()['id']}", headers=bearer(admin)
    )
    assert (refused.status_code, refused.json()["code"]) == (409, "review_not_draft")


async def test_a_draft_gp_lead_review_is_withdrawn_by_an_administrator(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    org_id, admin = await org_with_admin(client, make_actor)
    slot_id = await a_slot(db_session, org_id)
    url = f"/api/v1/orgs/kings/slots/{slot_id}/gp-lead-review"
    await client.put(url, json={"revision": 0, "notes": "half", "status": "draft"}, headers=bearer(admin))

    withdrawn = await client.delete(url, headers=bearer(admin))
    assert withdrawn.status_code == 204, withdrawn.text
    assert (await client.get(url, headers=bearer(admin))).json() is None
    again = await client.delete(url, headers=bearer(admin))
    assert (again.status_code, again.json()["code"]) == (404, "review_not_found")
