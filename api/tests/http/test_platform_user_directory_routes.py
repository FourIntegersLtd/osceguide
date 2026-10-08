"""The account directory: the retiring B2C admin's user list, served across
every exam at once.

Each column there was a fact a different slice owns here, so each test stages
the fact the way production produces it — a checkout webhook, a practice-set
attempt, a grant, a sign-in — and reads it back as one row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from tests.http.test_billing_routes import checkout_event, post_event
from tests.http.test_station_sets_routes import a_learner, a_station_version
from tests.support.billing import a_plan
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

DIRECTORY = "/api/v1/platform/directory"


async def a_person(session: AsyncSession, email: str, *, exam_code: str | None = None) -> uuid.UUID:
    user = await identity_repo.create_user(
        session, email=email, name=email.split("@")[0], password_hash=None, exam_code=exam_code
    )
    await session.flush()
    return user.id


async def rows_by_email(client: AsyncClient, root: str, query: str = "") -> dict[str, dict]:
    listed = await client.get(f"{DIRECTORY}?limit=100&{query}", headers=bearer(root))
    assert listed.status_code == 200, listed.text
    return {row["email"]: row for row in listed.json()["items"]}


async def test_a_row_carries_the_old_consoles_seven_columns(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    buyer = await a_person(db_session, "buyer@example.com", exam_code="sca")
    assert (await post_event(client, checkout_event("evt_dir", "buyer@example.com"))).status_code == 200
    await identity_repo.create_refresh_chain(
        db_session, user_id=buyer, token_hash="h1", expires_at=datetime.now(UTC) + timedelta(days=1)
    )
    await db_session.flush()

    row = (await rows_by_email(client, root))["buyer@example.com"]
    assert row["id"] == str(buyer)
    assert row["status"] == "active"
    assert row["exam_code"] == "sca"
    assert row["signed_in"] is True
    assert row["has_paid"] is True
    assert row["plan_code"] == "one_month"
    assert row["last_paid_at"] is not None
    assert row["access_ends_at"] is not None
    assert row["live_exam_codes"] == ["sca"]
    assert row["attempt_count"] == 0


async def test_an_account_that_never_paid_or_signed_in_reads_as_such(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_person(db_session, "quiet@example.com")

    row = (await rows_by_email(client, root))["quiet@example.com"]
    assert row["signed_in"] is False
    assert row["has_paid"] is False
    assert row["plan_code"] is None
    assert row["access_ends_at"] is None
    assert row["live_exam_codes"] == []
    assert row["exam_code"] is None


async def test_the_access_facet_splits_paid_trial_and_not_started(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The old filter modal's three states, from payments and attempts rather
    than a `has_paid` flag and the length of an array."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_person(db_session, "paid@example.com")
    assert (await post_event(client, checkout_event("evt_paid", "paid@example.com"))).status_code == 200
    await a_person(db_session, "idle@example.com")
    trialist = await a_learner(client, db_session, make_actor, "trial@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(trialist),
        )
    ).json()
    entry = created["entries"][0]["id"]
    assert (
        await client.post(
            f"/api/v1/me/station-sets/{created['id']}/entries/{entry}/attempts", headers=bearer(trialist)
        )
    ).status_code == 201

    assert set(await rows_by_email(client, root, "access=paid")) == {"paid@example.com"}
    assert set(await rows_by_email(client, root, "access=trial")) == {"trial@example.com"}
    not_started = set(await rows_by_email(client, root, "access=not_started"))
    assert "idle@example.com" in not_started
    assert not_started.isdisjoint({"paid@example.com", "trial@example.com"})
    assert (await rows_by_email(client, root, "access=trial"))["trial@example.com"]["attempt_count"] == 1


async def test_the_exam_facet_matches_the_chosen_exam_or_a_live_grant(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    sca = await ensure_exam(db_session, "sca")
    plab = await ensure_exam(db_session, "plab")
    await a_person(db_session, "chose.sca@example.com", exam_code="sca")
    granted = await a_person(db_session, "granted.sca@example.com", exam_code="plab")
    await ent_repo.grant(db_session, user_id=granted, exam_id=sca.id, source="admin")
    lapsed = await a_person(db_session, "lapsed.sca@example.com")
    await ent_repo.grant(
        db_session,
        user_id=lapsed,
        exam_id=sca.id,
        source="purchase",
        ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    await a_person(db_session, "plab.only@example.com", exam_code="plab")
    await db_session.flush()
    _ = plab

    on_sca = set(await rows_by_email(client, root, "exam_code=sca"))
    assert on_sca == {"chose.sca@example.com", "granted.sca@example.com"}
    on_plab = set(await rows_by_email(client, root, "exam_code=plab"))
    assert on_plab == {"granted.sca@example.com", "plab.only@example.com"}


async def test_status_plan_and_search_facets(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_person(db_session, "gone@example.com")
    await a_person(db_session, "Alice Example", exam_code=None) if False else None
    named = await identity_repo.create_user(
        db_session, email="a.n.other@example.com", name="Alice Example", password_hash=None
    )
    await db_session.flush()
    assert (await post_event(client, checkout_event("evt_plan", "gone@example.com"))).status_code == 200
    gone = await identity_repo.user_by_email(db_session, "gone@example.com")
    assert gone is not None
    deactivated = await client.patch(
        f"/api/v1/platform/users/{gone.id}", json={"status": "deactivated"}, headers=bearer(root)
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "deactivated"

    assert set(await rows_by_email(client, root, "status=deactivated")) == {"gone@example.com"}
    assert set(await rows_by_email(client, root, "plan_code=one_month")) == {"gone@example.com"}
    assert set(await rows_by_email(client, root, "plan_code=six_month")) == set()
    assert set(await rows_by_email(client, root, "q=alice")) == {"a.n.other@example.com"}
    assert (await rows_by_email(client, root, "q=alice"))["a.n.other@example.com"]["id"] == str(named.id)
    assert set(await rows_by_email(client, root, "q=gone")) == {"gone@example.com"}


async def test_the_summary_counts_each_exam_the_way_the_old_filter_did(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    await a_person(db_session, "p1@example.com", exam_code="sca")
    assert (await post_event(client, checkout_event("evt_s1", "p1@example.com"))).status_code == 200
    await a_person(db_session, "n1@example.com", exam_code="sca")
    await a_person(db_session, "nowhere@example.com")

    summary = await client.get(f"{DIRECTORY}/summary", headers=bearer(root))
    assert summary.status_code == 200, summary.text
    body = summary.json()
    sca = next(exam for exam in body["exams"] if exam["code"] == "sca")
    assert sca["name"]
    assert sca["users"] == 2
    assert sca["paid"] == 1
    assert sca["trial"] == 0
    assert sca["not_started"] == 1
    # root and `nowhere` name no exam and hold no grant.
    assert body["unassigned"] == 2
    assert body["total"] == 4
    assert set(await rows_by_email(client, root, "unassigned=true")) == {
        "root@osceguide.com",
        "nowhere@example.com",
    }
    # `unassigned` wins over an exam it would contradict.
    assert set(await rows_by_email(client, root, "unassigned=true&exam_code=sca")) == {
        "root@osceguide.com",
        "nowhere@example.com",
    }


async def test_the_summary_counts_payers_and_trialists_whatever_exam_they_name(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """B27: the Paid tile summed the exams, so a payer naming no exam whose grant
    had lapsed counted nowhere, and the tile read 1 while the Paid filter listed 37."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    await a_plan(db_session)
    lapsed = await a_person(db_session, "lapsed@example.com")
    assert (await post_event(client, checkout_event("evt_lapsed", "lapsed@example.com"))).status_code == 200
    for grant in await ent_repo.for_user(db_session, lapsed):
        await ent_repo.revoke(db_session, grant.id, at=datetime.now(UTC) - timedelta(days=1))
    await db_session.flush()
    trialist = await a_learner(client, db_session, make_actor, "trial@example.com")
    version = await a_station_version(db_session)
    created = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(trialist),
        )
    ).json()
    entry = created["entries"][0]["id"]
    assert (
        await client.post(
            f"/api/v1/me/station-sets/{created['id']}/entries/{entry}/attempts", headers=bearer(trialist)
        )
    ).status_code == 201

    body = (await client.get(f"{DIRECTORY}/summary", headers=bearer(root))).json()

    assert body["paid"] == len(await rows_by_email(client, root, "access=paid")) == 1
    assert body["trial"] == len(await rows_by_email(client, root, "access=trial")) == 1
    assert body["unassigned_paid"] == 1
    assert sum(exam["paid"] for exam in body["exams"]) == 0


async def test_the_detail_now_says_which_state_the_account_is_in_and_takes_the_two_new_fields(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """`status` was never on the detail, so the console's Deactivate button
    could not tell the two states apart. `exam_date` and the reading
    arrangement were columns nothing wrote."""
    root = await make_actor("root@osceguide.com", platform_admin=True)
    person = await a_person(db_session, "detail@example.com")

    before = await client.get(f"/api/v1/platform/users/{person}", headers=bearer(root))
    assert before.status_code == 200, before.text
    assert before.json()["status"] == "active"
    assert before.json()["exam_date"] is None
    assert before.json()["needs_extra_time"] is False
    assert before.json()["custom_reading_seconds"] is None

    updated = await client.patch(
        f"/api/v1/platform/users/{person}",
        json={"exam_date": "2026-11-03", "needs_extra_time": True, "custom_reading_seconds": 120},
        headers=bearer(root),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["exam_date"] == "2026-11-03"
    assert updated.json()["needs_extra_time"] is True
    assert updated.json()["custom_reading_seconds"] == 120

    refused = await client.patch(
        f"/api/v1/platform/users/{person}", json={"custom_reading_seconds": 3660}, headers=bearer(root)
    )
    assert refused.status_code == 422

    row = await client.get(f"{DIRECTORY}/users/{person}", headers=bearer(root))
    assert row.status_code == 200, row.text
    assert row.json()["email"] == "detail@example.com"
    missing = await client.get(f"{DIRECTORY}/users/{uuid.uuid4()}", headers=bearer(root))
    assert missing.status_code == 404
    assert missing.json()["code"] == "user_not_found"


async def test_the_directory_is_the_consoles_alone(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    member = await make_actor("member@example.com")
    for path in (DIRECTORY, f"{DIRECTORY}/summary", f"{DIRECTORY}/users/{uuid.uuid4()}"):
        refused = await client.get(path, headers=bearer(member))
        assert refused.status_code == 403, path
