"""The free trial's two-week window, route by route.

A trial is fourteen days from the account's first use (`UserRef.trial_started_at`). AI stations are
also capped at three stations and three attempts each; peer practice (the live queue and the
marketplace) is capped by the window alone, so using up the AI stations never closes it. Once the
window has closed every gated route answers 403 `not_entitled` with the reason `trial_expired`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import repository as attempts_repo
from app.features.identity import repository as identity_repo
from app.features.identity.models import User
from tests.http.test_media_routes import an_exam_item
from tests.http.test_peer_practice_routes import voice_tokens  # noqa: F401 - fixture
from tests.http.test_station_sets_routes import a_station_version
from tests.support.catalog import create_exam
from tests.support.fakes import FakeVectorIndex
from tests.support.library import publish_library_station
from tests.support.peer_practice import matched_pair
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime.now(UTC)


@pytest.fixture
def index(client: AsyncClient) -> FakeVectorIndex:
    """Replace the media search index with a fake, through the app's own seam."""
    from app.features.media.service_search import get_vector_index

    fake = FakeVectorIndex()
    client._transport.app.dependency_overrides[get_vector_index] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def age(db_session: AsyncSession, email: str, days: int) -> None:
    """Make this account `days` old, which is how long its trial has been running."""
    await db_session.execute(
        update(User).where(User.email == email).values(created_at=NOW - timedelta(days=days))
    )
    await db_session.flush()


async def sat_three_ai_stations(db_session: AsyncSession, email: str) -> None:
    """Finish three different practice stations, which uses up the AI stations of a trial."""
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await sat_three_ai_stations_for(db_session, user.id)


async def sat_three_ai_stations_for(db_session: AsyncSession, user_id) -> None:  # type: ignore[no-untyped-def]
    """The same, for a user already known by id."""
    exam_id = (await publish_library_exam(db_session)).exam_id
    for number in range(3):
        version_id = await publish_library_station(db_session, title=f"Used {number}")
        attempt = await attempts_repo.create_attempt(
            db_session,
            kind="practice",
            user_id=user_id,
            exam_id=exam_id,
            org_id=None,
            station_version_id=version_id,
        )
        await attempts_repo.set_status(db_session, attempt.id, status="running", at=NOW)
        await attempts_repo.set_status(db_session, attempt.id, status="interaction_complete", at=NOW)
    await db_session.flush()


async def publish_library_exam(db_session: AsyncSession):  # type: ignore[no-untyped-def]
    """The SCA exam, as a row with an `exam_id`."""
    from tests.support.catalog import ensure_exam

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None

    class _Exam:
        exam_id = exam.id

    return _Exam


def expired(response) -> None:  # type: ignore[no-untyped-def]
    """The refusal every gated route gives once the window has closed."""
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "not_entitled"
    assert response.json()["details"]["reason"] == "trial_expired"


# --- AI stations ----------------------------------------------------------------------------------


async def test_ai_attempt_is_refused_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("w-ai@example.com")
    await publish_library_exam(db_session)
    await age(db_session, "w-ai@example.com", 30)

    expired(
        await client.post(
            "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
        )
    )


async def _a_set_then_aged(client, db_session, make_actor, email):  # type: ignore[no-untyped-def]
    """A token, a set built while inside the window, and its first entry; then the account ages past it."""
    token = await make_actor(email)
    version = await a_station_version(db_session)
    built = await client.post(
        "/api/v1/me/station-sets",
        json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
        headers=bearer(token),
    )
    assert built.status_code == 201, built.text
    await age(db_session, email, 30)
    return token, version, built.json()


async def test_opening_a_practice_set_station_is_refused_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, _version, built = await _a_set_then_aged(client, db_session, make_actor, "w-set-open@example.com")

    expired(
        await client.post(
            f"/api/v1/me/station-sets/{built['id']}/entries/{built['entries'][0]['id']}/attempts",
            headers=bearer(token),
        )
    )


async def test_building_a_practice_set_is_refused_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token, version, _built = await _a_set_then_aged(client, db_session, make_actor, "w-set-build@example.com")

    expired(
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "Again", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    )


async def test_an_attempt_opened_inside_the_window_cannot_begin_after_it(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The start boundary: the worker's first fetch re-checks access (S-11)."""
    from tests.http.test_station_sets_routes import worker_headers

    token = await make_actor("w-begin@example.com")
    version = await a_station_version(db_session)
    built = (
        await client.post(
            "/api/v1/me/station-sets",
            json={"name": "W", "exam_code": "sca", "station_version_ids": [str(version)]},
            headers=bearer(token),
        )
    ).json()
    opened = await client.post(
        f"/api/v1/me/station-sets/{built['id']}/entries/{built['entries'][0]['id']}/attempts",
        headers=bearer(token),
    )
    assert opened.status_code == 201, opened.text
    await age(db_session, "w-begin@example.com", 30)

    fetched = await client.get(
        f"/api/worker/attempts/{opened.json()['attempt_id']}", headers=worker_headers()
    )

    expired(fetched)


# --- Peer practice: the window alone --------------------------------------------------------------


async def test_a_trial_that_has_used_its_ai_stations_may_still_queue_for_a_peer(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Peer practice is limited by time, not by a count of stations."""
    token = await make_actor("w-peer-count@example.com")
    await sat_three_ai_stations(db_session, "w-peer-count@example.com")

    queued = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
    )
    # Last, because a refusal rolls back the test's session.
    ai = await client.post(
        "/api/v1/attempts", json={"kind": "practice", "exam_code": "sca"}, headers=bearer(token)
    )

    assert queued.status_code == 201, queued.text
    assert ai.status_code == 403, "the AI stations are used up"


async def test_peer_sessions_do_not_use_up_the_ai_stations(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The trial counts a finished practice, never a peer session."""
    row = await matched_pair(client, make_actor, db_session, "w-peer-free")
    doctor_id, exam_id = row.doctor_user_id, row.exam_id
    peer = await attempts_repo.create_attempt(
        db_session,
        kind="peer",
        user_id=doctor_id,
        exam_id=exam_id,
        org_id=None,
        station_version_id=row.station_version_id,
        peer_session_id=row.id,
    )
    practice = await attempts_repo.create_attempt(
        db_session,
        kind="practice",
        user_id=doctor_id,
        exam_id=exam_id,
        org_id=None,
        station_version_id=row.station_version_id,
    )
    for attempt in (peer, practice):
        await attempts_repo.set_status(db_session, attempt.id, status="running", at=NOW)
        await attempts_repo.set_status(db_session, attempt.id, status="interaction_complete", at=NOW)

    counted = await attempts_repo.attempts_counted_by_trial(db_session, doctor_id, exam_id)

    assert [trial_attempt.kind for trial_attempt in counted] == ["practice"]


async def _marked_in_a_session_that_started(
    client: AsyncClient, db_session: AsyncSession, make_actor, monkeypatch, tag: str, *, started_days_ago: int
):  # type: ignore[no-untyped-def]
    """Transcribe a finished peer session whose doctor's account is 20 days old and out of AI stations.

    The session started `started_days_ago` days ago, so the doctor's trial was running or over then.
    """
    from app.features.peer_practice import repository_sessions, service_feedback
    from app.features.peer_practice.models import PracticeSession
    from tests.http.test_peer_recording import _fake_recording_in_the_bucket, _two_turns
    from tests.support.fakes import FakeTranscriber
    from tests.support.peer_practice import stopped_pair

    row = await stopped_pair(client, make_actor, db_session, tag)
    await sat_three_ai_stations_for(db_session, row.doctor_user_id)
    await db_session.execute(
        update(User).where(User.id == row.doctor_user_id).values(created_at=NOW - timedelta(days=20))
    )
    await db_session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == row.id)
        .values(started_at=NOW - timedelta(days=started_days_ago))
    )
    await db_session.flush()
    _fake_recording_in_the_bucket(monkeypatch)

    attempt_id = await service_feedback.build_feedback(
        db_session, row.id, now=NOW, transcriber=FakeTranscriber(), diarise=_two_turns
    )
    return attempt_id, await repository_sessions.session_by_id(db_session, row.id)


async def test_a_session_sat_inside_the_window_is_marked_after_it_closes(
    client: AsyncClient, db_session: AsyncSession, make_actor, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """The window is judged when the session started: late transcription must not lose the mark.

    Also covers the used-up AI stations: marking a peer session needs only the window.
    """
    attempt_id, session_row = await _marked_in_a_session_that_started(
        client, db_session, make_actor, monkeypatch, "w-mark-late", started_days_ago=10
    )

    assert attempt_id is not None
    assert session_row is not None
    assert session_row.doctor_attempt_id == attempt_id
    assert session_row.recording_state != "failed"


async def test_a_session_sat_after_the_window_is_not_marked(
    client: AsyncClient, db_session: AsyncSession, make_actor, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    attempt_id, session_row = await _marked_in_a_session_that_started(
        client, db_session, make_actor, monkeypatch, "w-mark-none", started_days_ago=1
    )

    assert attempt_id is None
    assert session_row is not None
    assert session_row.doctor_attempt_id is None
    assert session_row.recording_state == "failed"
    assert (session_row.recording_error or "").startswith("not entitled when marking")


async def test_the_live_queue_is_refused_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("w-queue@example.com")
    await publish_library_station(db_session, "sca")
    await age(db_session, "w-queue@example.com", 30)

    expired(
        await client.post("/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token))
    )


async def test_a_matched_pair_cannot_enter_the_room_once_the_window_closes(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,
    voice_tokens,  # noqa: F811
) -> None:  # type: ignore[no-untyped-def]
    from app.features.peer_practice import service
    from tests.http.test_peer_practice_routes import accept

    first = await make_actor("w-room-a@example.com")
    second = await make_actor("w-room-b@example.com")
    await publish_library_station(db_session, "sca")
    for token in (first, second):
        assert (
            await client.post("/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token))
        ).status_code == 201
    exam = (await publish_library_exam(db_session)).exam_id
    matched = await service.match_waiting(db_session, exam)
    assert matched is not None
    session_id = matched.id
    await db_session.flush()
    await accept(client, session_id, first)
    await accept(client, session_id, second)
    inside = await client.post(
        f"/api/v1/me/practice-sessions/{session_id}/voice-token", headers=bearer(first)
    )
    assert inside.status_code == 200, inside.text

    await age(db_session, "w-room-a@example.com", 30)

    still_in = await client.post(
        f"/api/v1/me/practice-sessions/{session_id}/voice-token", headers=bearer(second)
    )
    assert still_in.status_code == 200, "the partner's own trial is untouched"
    # Last, because a refusal rolls back the test's session.
    expired(
        await client.post(f"/api/v1/me/practice-sessions/{session_id}/voice-token", headers=bearer(first))
    )


async def test_a_trial_with_its_ai_stations_used_up_may_still_offer_a_marketplace_slot(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await publish_library_exam(db_session)
    token = await make_actor("w-market-used@example.com")
    await sat_three_ai_stations(db_session, "w-market-used@example.com")

    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": (NOW + timedelta(days=1)).isoformat()},
        headers=bearer(token),
    )

    assert offered.status_code == 201, offered.text


async def test_offering_a_marketplace_slot_is_refused_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await publish_library_exam(db_session)
    token = await make_actor("w-market-old@example.com")
    await age(db_session, "w-market-old@example.com", 30)

    expired(
        await client.post(
            "/api/v1/marketplace/slots",
            json={"exam_code": "sca", "starts_at": (NOW + timedelta(days=1)).isoformat()},
            headers=bearer(token),
        )
    )


async def test_claiming_a_marketplace_slot_is_refused_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await publish_library_exam(db_session)
    owner = await make_actor("w-claim-owner@example.com")
    taker = await make_actor("w-claim-taker@example.com")
    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": (NOW + timedelta(days=1)).isoformat()},
        headers=bearer(owner),
    )
    assert offered.status_code == 201, offered.text
    await age(db_session, "w-claim-taker@example.com", 30)

    expired(
        await client.post(f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(taker))
    )


async def test_a_booked_marketplace_session_cannot_be_joined_after_the_window(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await publish_library_exam(db_session)
    owner = await make_actor("w-book-owner@example.com")
    taker = await make_actor("w-book-taker@example.com")
    soon = (NOW + timedelta(minutes=5)).isoformat()
    offered = await client.post(
        "/api/v1/marketplace/slots", json={"exam_code": "sca", "starts_at": soon}, headers=bearer(owner)
    )
    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(taker)
    )
    assert claimed.status_code == 201, claimed.text
    await age(db_session, "w-book-taker@example.com", 30)

    expired(await client.post(f"/api/v1/me/peer-sessions/{claimed.json()['id']}/join", headers=bearer(taker)))


async def _grant(db_session: AsyncSession, email: str) -> None:
    """Give this account a live purchase of the SCA exam, and age it past the trial."""
    from app.features.entitlements import repository as ent_repo

    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await ent_repo.grant(
        db_session,
        user_id=user.id,
        exam_id=(await publish_library_exam(db_session)).exam_id,
        source="purchase",
        ends_at=NOW + timedelta(days=30),
    )
    await age(db_session, email, 30)


async def test_a_paying_account_older_than_the_trial_still_uses_the_queue_and_the_room(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,
    voice_tokens,  # noqa: F811
) -> None:  # type: ignore[no-untyped-def]
    """`window_only` must not skip a live grant: only the trial's counts are ignored."""
    from app.features.peer_practice import service
    from tests.http.test_peer_practice_routes import accept

    first = await make_actor("w-paid-q-a@example.com")
    second = await make_actor("w-paid-q-b@example.com")
    await publish_library_station(db_session, "sca")
    for email in ("w-paid-q-a@example.com", "w-paid-q-b@example.com"):
        await _grant(db_session, email)
    for token in (first, second):
        queued = await client.post(
            "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
        )
        assert queued.status_code == 201, queued.text
    matched = await service.match_waiting(db_session, (await publish_library_exam(db_session)).exam_id)
    assert matched is not None
    await db_session.flush()

    await accept(client, matched.id, first)
    await accept(client, matched.id, second)

    for token in (first, second):
        voice = await client.post(
            f"/api/v1/me/practice-sessions/{matched.id}/voice-token", headers=bearer(token)
        )
        assert voice.status_code == 200, voice.text


async def test_a_paying_account_older_than_the_trial_still_offers_claims_and_joins_a_slot(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    await publish_library_exam(db_session)
    owner = await make_actor("w-paid-m-a@example.com")
    taker = await make_actor("w-paid-m-b@example.com")
    for email in ("w-paid-m-a@example.com", "w-paid-m-b@example.com"):
        await _grant(db_session, email)

    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": (NOW + timedelta(minutes=5)).isoformat()},
        headers=bearer(owner),
    )
    assert offered.status_code == 201, offered.text
    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(taker)
    )
    assert claimed.status_code == 201, claimed.text
    for token in (owner, taker):
        joined = await client.post(
            f"/api/v1/me/peer-sessions/{claimed.json()['id']}/join", headers=bearer(token)
        )
        assert joined.status_code == 200, joined.text
        assert joined.json()["practice_session_id"] is not None


async def _pair_pending_accept(client, db_session, make_actor, tag):  # type: ignore[no-untyped-def]
    """Two fresh trials queued and paired, neither having accepted yet."""
    from app.features.peer_practice import service

    first = await make_actor(f"{tag}-a@example.com")
    second = await make_actor(f"{tag}-b@example.com")
    await publish_library_station(db_session, "sca")
    for token in (first, second):
        queued = await client.post(
            "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
        )
        assert queued.status_code == 201, queued.text
    matched = await service.match_waiting(db_session, (await publish_library_exam(db_session)).exam_id)
    assert matched is not None
    await db_session.flush()
    return matched.id, first, second


async def test_a_match_made_on_the_last_day_cannot_be_accepted_after_it(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    session_id, first, second = await _pair_pending_accept(client, db_session, make_actor, "w-acc-late")
    await age(db_session, "w-acc-late-b@example.com", 30)

    expired(await client.post(f"/api/v1/me/practice-sessions/{session_id}/accept", headers=bearer(second)))


async def test_a_pairing_ends_instead_of_making_a_room_the_partner_cannot_enter(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The partner's window closed while they waited: no room, and the accepter is queued again."""
    from sqlalchemy import select

    from app.features.peer_practice.models import QueueEntry
    from tests.http.test_peer_practice_routes import accept

    session_id, first, second = await _pair_pending_accept(client, db_session, make_actor, "w-acc-strand")
    await accept(client, session_id, first)
    await age(db_session, "w-acc-strand-a@example.com", 30)

    settled = await client.post(f"/api/v1/me/practice-sessions/{session_id}/accept", headers=bearer(second))

    assert settled.status_code == 200, settled.text
    assert settled.json()["status"] == "ended"
    assert settled.json()["end_reason"] == "partner_unavailable"
    second_user = await identity_repo.user_by_email(db_session, "w-acc-strand-b@example.com")
    assert second_user is not None
    waiting = (
        await db_session.scalars(
            select(QueueEntry).where(QueueEntry.user_id == second_user.id, QueueEntry.status == "waiting")
        )
    ).all()
    assert len(waiting) == 1, "the person still inside their trial goes back in the queue"


async def test_a_booked_session_is_called_off_when_the_other_person_trial_has_closed(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """No room is made for someone who could not enter it, so nobody is left waiting in one."""
    await publish_library_exam(db_session)
    owner = await make_actor("w-book-gone-a@example.com")
    taker = await make_actor("w-book-gone-b@example.com")
    offered = await client.post(
        "/api/v1/marketplace/slots",
        json={"exam_code": "sca", "starts_at": (NOW + timedelta(minutes=5)).isoformat()},
        headers=bearer(owner),
    )
    claimed = await client.post(
        f"/api/v1/marketplace/slots/{offered.json()['id']}/claim", headers=bearer(taker)
    )
    assert claimed.status_code == 201, claimed.text
    await age(db_session, "w-book-gone-a@example.com", 30)

    joined = await client.post(f"/api/v1/me/peer-sessions/{claimed.json()['id']}/join", headers=bearer(taker))

    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "cancelled"
    assert joined.json()["practice_session_id"] is None


# --- Study material -------------------------------------------------------------------------------


async def test_study_material_locks_when_the_window_closes(
    client: AsyncClient, db_session: AsyncSession, make_actor, index: FakeVectorIndex
) -> None:  # type: ignore[no-untyped-def]
    admin = await make_actor("w-media-admin@osceguide.com", platform_admin=True)
    await create_exam(client, admin, code="sca")
    item = await an_exam_item(client, admin, exam_code="sca")
    fresh = await make_actor("w-media-fresh@example.com", exam_code="sca")
    old = await make_actor("w-media-old@example.com", exam_code="sca")
    await age(db_session, "w-media-old@example.com", 30)
    await db_session.commit()

    opened = (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(fresh))).json()
    closed = (await client.get(f"/api/v1/media/{item['slug']}", headers=bearer(old))).json()

    assert opened["locked"] is False
    assert opened["content"] == {"slides": ["Angina", "Reflux"]}
    assert closed["locked"] is True
    assert closed["content"] is None
