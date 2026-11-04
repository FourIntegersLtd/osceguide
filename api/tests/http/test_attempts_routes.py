"""Creating and reading attempts, and the entitlement gate in front of them."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.entitlements import repository as ent_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
async def an_exam_to_attempt(db_session: AsyncSession) -> None:
    """Every test here names an exam, and nothing is seeded any more."""
    await ensure_exam(db_session, "sca")


async def entitle(session: AsyncSession, token_user: uuid.UUID, code: str = "sca") -> None:
    exam = await ensure_exam(session, code)
    assert exam is not None
    await ent_repo.grant(
        session,
        user_id=token_user,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await session.flush()


async def test_starting_an_attempt_needs_an_entitlement(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """No entitlement and no trial left is a refusal.

    This used to pass with a brand-new account, because the free trial was
    never consulted — `trial=None` made `decide` skip the branch. A new account
    is exactly the case that *should* be allowed, so the account is aged past
    the trial window to test what this was always meant to test.
    """
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("nopay@example.com")
    await db_session.execute(
        update(User)
        .where(User.email == "nopay@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert response.status_code == 403
    assert response.json()["code"] == "not_entitled"


async def test_an_entitled_user_may_start_an_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("paid@example.com")
    from app.features.identity import repository as identity_repo

    user = await identity_repo.user_by_email(db_session, "paid@example.com")
    assert user is not None
    await entitle(db_session, user.id)

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert response.json()["kind"] == "practice"


async def test_an_unknown_exam_is_refused(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("x@example.com")
    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "mrcp"}, headers=bearer(token)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_reading_someone_elses_attempt_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    owner_token = await make_actor("owner@example.com")
    owner = await identity_repo.user_by_email(db_session, "owner@example.com")
    assert owner is not None
    await entitle(db_session, owner.id)
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(owner_token)
    )
    attempt_id = created.json()["id"]

    stranger = await make_actor("stranger@example.com")
    response = await client.get(f"/api/v1/attempts/{attempt_id}", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "attempt_not_yours"


async def test_an_owner_reads_their_own_attempt_and_transcript(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    token = await make_actor("me@example.com")
    user = await identity_repo.user_by_email(db_session, "me@example.com")
    assert user is not None
    await entitle(db_session, user.id)
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    attempt_id = created.json()["id"]

    assert (await client.get(f"/api/v1/attempts/{attempt_id}", headers=bearer(token))).status_code == 200
    transcript = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(token))
    assert transcript.status_code == 200
    assert transcript.json()["messages"] == []
    results = await client.get(f"/api/v1/attempts/{attempt_id}/result", headers=bearer(token))
    assert results.json()["items"] == []


async def test_my_entitlements_are_listed(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    token = await make_actor("list@example.com")
    user = await identity_repo.user_by_email(db_session, "list@example.com")
    assert user is not None
    await entitle(db_session, user.id)
    response = await client.get("/api/v1/me/entitlements", headers=bearer(token))
    assert response.status_code == 200
    assert [e["exam_code"] for e in response.json()["items"]] == ["sca"]
    assert response.json()["items"][0]["live"] is True


# --------------------------------------------------------------------------
# The free trial (E1/E2)
# --------------------------------------------------------------------------


async def test_a_new_user_gets_the_free_trial(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """`trial_available` was written, unit-tested, and never given a trial to test.

    `attempts.service` passed `trial=None`, and `decide` skips the trial branch
    entirely when it is None — so a brand-new account with no entitlement was
    refused outright and nobody could try the product.
    """
    token = await make_actor("trialist@example.com")

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert response.status_code == 201, response.text


async def test_the_trial_runs_out_after_three_attempts(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Three finished stations end the trial.

    These attempts name no station, and each such attempt counts as a station
    of its own. The retry rule (the same station again) is tested through the
    database in `test_a_trial_station_can_be_retried_without_using_another`.
    """
    from app.features.attempts import repository as attempts_repo
    from app.features.identity import repository as identity_repo

    token = await make_actor("threeonly@example.com")
    user = await identity_repo.user_by_email(db_session, "threeonly@example.com")
    assert user is not None

    for _ in range(3):
        created = await client.post(
            "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
        )
        assert created.status_code == 201, created.text
        attempt_id = uuid.UUID(created.json()["id"])
        await attempts_repo.set_status(db_session, attempt_id, status="running", at=NOW)
        await attempts_repo.set_status(db_session, attempt_id, status="interaction_complete", at=NOW)
    await db_session.flush()

    refused = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "not_entitled"
    assert refused.json()["details"]["reason"] == "trial_exhausted"


async def test_a_trial_station_can_be_retried_without_using_another(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The trial counts stations: a station may be finished three times, and that is one station used."""
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts import service as attempts_service
    from app.features.identity import repository as identity_repo
    from app.features.stations import repository as stations_repo

    await make_actor("retrier@example.com")
    user = await identity_repo.user_by_email(db_session, "retrier@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert user is not None and exam is not None
    version_ids = []
    for title in ("Chest pain", "Low mood"):
        station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title=title)
        version = await stations_repo.add_version(
            db_session, None, station_id=station.id, version=1, content={"station_name": title}
        )
        version_ids.append(version.id)
    retried, untouched = version_ids

    async def finish_one(station_version_id: uuid.UUID) -> None:
        attempt = await attempts_repo.create_attempt(
            db_session,
            kind="practice",
            user_id=user.id,
            exam_id=exam.id,
            station_version_id=station_version_id,
        )
        await attempts_repo.set_status(db_session, attempt.id, status="running", at=NOW)
        await attempts_repo.set_status(db_session, attempt.id, status="interaction_complete", at=NOW)

    async def trial(station_version_id: uuid.UUID):  # type: ignore[no-untyped-def]
        state = await attempts_service.trial_state_for(
            db_session, user_id=user.id, exam_id=exam.id, station_version_id=station_version_id
        )
        assert state is not None
        return state

    await finish_one(retried)
    await finish_one(retried)
    await db_session.flush()

    after_two = await trial(retried)
    assert (after_two.completed_station_count, after_two.completed_on_this_station) == (1, 2)
    # A station not sat yet is not a retry, and only one trial station is used so far.
    fresh = await trial(untouched)
    assert (fresh.completed_station_count, fresh.completed_on_this_station) == (1, None)

    await finish_one(retried)
    await db_session.flush()
    assert (await trial(retried)).completed_on_this_station == 3


async def test_an_old_account_has_no_trial_left(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Fourteen days, and the comparison is strict: a fifteen-day-old account is out."""
    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("veteran@example.com")
    await db_session.execute(
        update(User)
        .where(User.email == "veteran@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=15))
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert response.status_code == 403, response.text
    assert response.json()["details"]["reason"] == "trial_expired"


async def test_an_invited_accounts_trial_counts_from_its_first_sign_in(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """S-10: an invitation created thirty days ago and accepted today still gets its fourteen days.

    The trial was measured from `created_at`, so someone invited and left waiting arrived with
    the trial already spent.
    """
    from sqlalchemy import update

    from app.features.identity import repository as identity_repo
    from app.features.identity.models import User
    from app.features.identity.service_invitations import invite_user
    from app.features.identity.tokens import _hash_sync

    invited = await invite_user(db_session, email="late@example.com", name="Late", invited_to="Acme", now=NOW)
    await db_session.execute(
        update(User)
        .where(User.id == invited.id)
        .values(created_at=datetime.now(UTC) - timedelta(days=30), must_change_password=False)
    )
    await identity_repo.set_password_hash(db_session, invited.id, _hash_sync("a long enough passphrase"))
    await db_session.flush()

    login = await client.post(
        "/api/v1/auth/login", json={"email": "late@example.com", "password": "a long enough passphrase"}
    )
    assert login.status_code == 200, login.text
    response = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca"},
        headers=bearer(login.json()["access_token"]),
    )

    assert response.status_code == 201, response.text


# --------------------------------------------------------------------------
# Abandoning
# --------------------------------------------------------------------------


async def an_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession, email: str
) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    token = await make_actor(email)
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await entitle(db_session, user.id)
    created = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    return token, created.json()["id"]


async def test_a_candidate_can_walk_away_from_an_attempt(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Without this an abandoned attempt stays `running` forever.

    It holds the slot's one live attempt, so a re-dispatch is the only way out,
    and every screen that reads status counts it as in progress.
    """
    token, attempt_id = await an_attempt(client, make_actor, db_session, "quitter@example.com")

    response = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"

    read_back = await client.get(f"/api/v1/attempts/{attempt_id}", headers=bearer(token))
    assert read_back.json()["status"] == "failed"


async def test_an_attempt_already_finished_cannot_be_abandoned(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """There is a transcript being marked; throwing it away is not a candidate's to do."""
    from app.features.attempts import repository as attempts_repo
    from app.features.attempts.domain import Status

    token, attempt_id = await an_attempt(client, make_actor, db_session, "done@example.com")
    await attempts_repo.set_status(
        db_session, uuid.UUID(attempt_id), status=Status.RUNNING, at=datetime.now(UTC)
    )
    await attempts_repo.set_status(
        db_session,
        uuid.UUID(attempt_id),
        status=Status.INTERACTION_COMPLETE,
        at=datetime.now(UTC),
    )
    await db_session.flush()

    response = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_attempt_state"


async def test_abandoning_twice_is_refused_rather_than_silently_accepted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    token, attempt_id = await an_attempt(client, make_actor, db_session, "twice@example.com")
    await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    again = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(token))
    assert again.status_code == 409
    assert again.json()["code"] == "invalid_attempt_state"


async def test_abandoning_someone_elses_attempt_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    _, attempt_id = await an_attempt(client, make_actor, db_session, "mine@example.com")
    stranger = await make_actor("notmine@example.com")
    response = await client.post(f"/api/v1/attempts/{attempt_id}/abandon", headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["code"] == "attempt_not_yours"


async def test_a_client_cannot_attach_an_attempt_to_another_slices_record(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The reference ids are not the client's to choose.

    `POST /attempts` took `slot_id`, `set_entry_id`, `peer_session_id`,
    `source_attempt_id` and `room_name` straight from the body and stored them
    unverified, so anyone could hang their attempt off another organisation's
    exam slot or another person's set entry. `attempts` sits below every slice
    that owns those records and cannot check them, so the route no longer
    accepts them at all: each kind has a route on the slice that can.
    """
    token = await make_actor("forger@example.com")
    for field in ("slot_id", "set_entry_id", "peer_session_id", "source_attempt_id"):
        response = await client.post(
            "/api/v1/attempts",
            json={"kind": "practice", "exam_code": "sca", field: str(uuid.uuid4())},
            headers=bearer(token),
        )
        assert response.status_code == 201, response.text
        # Ignored rather than honoured: nothing the client sent reached the row.
        from app.features.attempts.models import Attempt

        attempt = await db_session.get(Attempt, uuid.UUID(response.json()["id"]))
        assert attempt is not None
        assert getattr(attempt, field) is None


async def test_the_kinds_another_slice_owns_are_not_offered_here(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A set station, a debrief, an exam slot and a peer session each have a
    route on the slice that can verify what they point at."""
    token = await make_actor("wrongkind@example.com")
    for kind in ("set_station", "debrief", "exam_slot", "peer"):
        response = await client.post(
            "/api/v1/attempts",
            json={"kind": kind, "exam_code": "sca"},
            headers=bearer(token),
        )
        assert response.status_code == 422, f"{kind}: {response.text}"


async def test_a_station_from_another_organisation_is_not_runnable(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Not found rather than forbidden: telling the two apart would make this
    route a way to enumerate another tenant's library."""
    from app.features.stations import repository as stations_repo
    from app.features.tenancy import repository as tenancy_repo

    token = await make_actor("outsider@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    other_org = await tenancy_repo.create_organization(
        db_session, slug=f"other-{uuid.uuid4().hex[:6]}", name="Other", org_type="institution"
    )
    await db_session.flush()
    station = await stations_repo.create_station(db_session, other_org.id, exam_id=exam.id, title="Theirs")
    version = await stations_repo.add_version(
        db_session, other_org.id, station_id=station.id, version=1, content={"station_name": "x"}
    )
    await stations_repo.set_version_status(
        db_session, other_org.id, version.id, status="published", at=NOW, by=None
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)},
        headers=bearer(token),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "station_not_found"


async def test_reopening_a_station_resumes_the_attempt_it_never_started(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A reload of the station screen used to open a fresh attempt each time, orphaning the last one
    and restarting the reading clock (staging, 2026-10-03). Until the consultation starts, opening
    the same station again hands back the same attempt; once it has started, a new one is opened."""
    from app.features.attempts import repository as attempts_repo
    from app.features.identity import repository as identity_repo
    from app.features.stations import repository as stations_repo

    token = await make_actor("reloader@example.com")
    user = await identity_repo.user_by_email(db_session, "reloader@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert user is not None and exam is not None
    await entitle(db_session, user.id)
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title="Elevated PSA")
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content={"station_name": "Elevated PSA"}
    )
    await stations_repo.set_version_status(db_session, None, version.id, status="published", at=NOW, by=None)
    await db_session.flush()
    body = {"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)}

    first = await client.post("/api/v1/attempts", json=body, headers=bearer(token))
    again = await client.post("/api/v1/attempts", json=body, headers=bearer(token))
    assert first.status_code == 201, first.text
    assert again.json()["id"] == first.json()["id"]

    await attempts_repo.set_status(db_session, uuid.UUID(first.json()["id"]), status="running", at=NOW)
    await db_session.flush()
    after_start = await client.post("/api/v1/attempts", json=body, headers=bearer(token))
    assert after_start.json()["id"] != first.json()["id"]


async def test_reopening_a_station_after_access_ended_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """S-11: the resume path ran before the entitlement gate, so a lapsed or refunded learner
    could reopen an unstarted attempt for as long as the row existed."""
    from sqlalchemy import update

    from app.features.entitlements.models import Entitlement
    from app.features.identity import repository as identity_repo
    from app.features.identity.models import User
    from app.features.stations import repository as stations_repo

    token = await make_actor("lapsed@example.com")
    user = await identity_repo.user_by_email(db_session, "lapsed@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert user is not None and exam is not None
    await entitle(db_session, user.id)
    station = await stations_repo.create_station(db_session, None, exam_id=exam.id, title="Chest pain")
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content={"station_name": "Chest pain"}
    )
    await stations_repo.set_version_status(db_session, None, version.id, status="published", at=NOW, by=None)
    await db_session.flush()
    body = {"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)}
    first = await client.post("/api/v1/attempts", json=body, headers=bearer(token))
    assert first.status_code == 201, first.text

    await db_session.execute(update(Entitlement).where(Entitlement.user_id == user.id).values(revoked_at=NOW))
    await db_session.execute(
        update(User).where(User.id == user.id).values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()

    again = await client.post("/api/v1/attempts", json=body, headers=bearer(token))
    assert again.status_code == 403
    assert again.json()["code"] == "not_entitled"


async def test_a_station_of_another_exam_is_not_runnable_on_this_exams_grant(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Holding exam A must not let a learner sit exam B's published station by naming A.

    A clean account, a grant for `sca`, a published `plab` station: entitlement was checked against
    the claimed exam and the station's own exam was never compared, so this started (201) and filed
    the attempt under the wrong exam.
    """
    from sqlalchemy import func, select

    from app.features.attempts.models import Attempt
    from app.features.identity import repository as identity_repo
    from app.features.stations import repository as stations_repo

    token = await make_actor("crossexam@example.com")
    user = await identity_repo.user_by_email(db_session, "crossexam@example.com")
    other = await ensure_exam(db_session, "plab")
    assert user is not None
    user_id = user.id
    await entitle(db_session, user_id, "sca")
    station = await stations_repo.create_station(db_session, None, exam_id=other.id, title="PLAB only")
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content={"station_name": "PLAB only"}
    )
    await stations_repo.set_version_status(db_session, None, version.id, status="published", at=NOW, by=None)
    await db_session.flush()

    response = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)},
        headers=bearer(token),
    )

    assert (response.status_code, response.json()["code"]) == (409, "station_exam_mismatch")
    started = await db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id)
    )
    assert started == 0


async def test_start_attempt_refuses_a_cross_exam_station_for_every_caller(
    make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The gate lives in `start_attempt`, so sets, peer practice and any later caller get it too."""
    from app.features.attempts import errors as attempt_errors
    from app.features.attempts import service as attempts_service
    from app.features.identity import repository as identity_repo
    from app.features.stations import repository as stations_repo

    await make_actor("svc-cross@example.com")
    user = await identity_repo.user_by_email(db_session, "svc-cross@example.com")
    other = await ensure_exam(db_session, "plab")
    assert user is not None
    user_id = user.id
    await entitle(db_session, user_id, "sca")
    station = await stations_repo.create_station(db_session, None, exam_id=other.id, title="PLAB only")
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content={"station_name": "PLAB only"}
    )
    await stations_repo.set_version_status(db_session, None, version.id, status="published", at=NOW, by=None)
    await db_session.flush()

    with pytest.raises(attempt_errors.StationExamMismatch):
        await attempts_service.start_attempt(
            db_session,
            user_id=user_id,
            kind="practice",
            exam_code="sca",
            now=NOW,
            station_version_id=version.id,
        )
