"""Queueing, matching and practising."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models import OutboundMessage
from app.features.peer_practice import service
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeVoiceTokens
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture
def voice_tokens(client: AsyncClient) -> FakeVoiceTokens:
    """Replace the LiveKit adapter with a recording fake, at this slice's seam."""
    from app.features.peer_practice.service_voice import get_voice_tokens

    fake = FakeVoiceTokens()
    client._transport.app.dependency_overrides[get_voice_tokens] = lambda: fake  # type: ignore[attr-defined]
    return fake


@pytest.fixture(autouse=True)
async def an_exam_to_queue_for(db_session: AsyncSession) -> None:
    """Every test here queues for an exam, and nothing is seeded any more.

    Autouse because it is a precondition of the whole file rather than of one
    test: there is no peer practice without something to practise.
    """
    await ensure_exam(db_session, "sca")


async def join(client: AsyncClient, token: str) -> dict:
    response = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def accept(client: AsyncClient, session_id, token: str) -> dict:  # type: ignore[no-untyped-def]
    """Accept a pending match on this caller's behalf, asserting it went through."""
    response = await client.post(f"/api/v1/me/practice-sessions/{session_id}/accept", headers=bearer(token))
    assert response.status_code == 200, response.text
    return response.json()


async def test_joining_gives_a_place_in_the_queue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("q1@example.com")
    status = await join(client, token)
    assert status["status"] == "waiting"
    assert status["position"] == 1


async def test_joining_twice_keeps_the_same_place(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """Somebody tapping a button again, not an error worth refusing."""
    token = await make_actor("q2@example.com")
    first = await join(client, token)
    second = await join(client, token)
    assert first["entry_id"] == second["entry_id"]


async def test_position_reflects_who_arrived_first(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    first_token = await make_actor("q3-a@example.com")
    second_token = await make_actor("q3-b@example.com")
    await join(client, first_token)
    second = await join(client, second_token)
    assert second["position"] == 2
    assert second["waiting_count"] == 2


async def test_leaving_removes_you(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("q4@example.com")
    entry = await join(client, token)
    removed = await client.delete(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(token))
    assert removed.status_code == 204

    status = await client.get(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(token))
    assert status.json()["status"] == "left"


async def test_someone_elses_queue_entry_is_not_found(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("q5@example.com")
    entry = await join(client, token)
    stranger = await make_actor("q5-b@example.com")
    response = await client.get(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(stranger))
    assert response.status_code == 404


async def test_two_waiting_people_are_matched(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    doctor_token = await make_actor("m1-a@example.com")
    patient_token = await make_actor("m1-b@example.com")
    first = await join(client, doctor_token)
    second = await join(client, patient_token)

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    for token, entry in ((doctor_token, first), (patient_token, second)):
        status = await client.get(f"/api/v1/peer-practice/queue/{entry['entry_id']}", headers=bearer(token))
        assert status.json()["status"] == "matched"
        assert status.json()["session_id"] == str(matched.id)


async def test_a_matched_pair_gets_opposite_roles_and_one_room(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("m2-a@example.com")
    b_token = await make_actor("m2-b@example.com")
    await join(client, a_token)
    await join(client, b_token)

    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    a_view = await client.get(f"/api/v1/me/practice-sessions/{matched.id}", headers=bearer(a_token))
    b_view = await client.get(f"/api/v1/me/practice-sessions/{matched.id}", headers=bearer(b_token))
    assert {a_view.json()["my_role"], b_view.json()["my_role"]} == {"doctor", "patient"}
    assert a_view.json()["room_name"] == b_view.json()["room_name"]
    assert a_view.json()["room_name"] == f"practice_{matched.id}"


async def test_a_stranger_cannot_see_the_session(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    await join(client, await make_actor("m3-a@example.com"))
    await join(client, await make_actor("m3-b@example.com"))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    stranger = await make_actor("m3-c@example.com")
    response = await client.get(f"/api/v1/me/practice-sessions/{matched.id}", headers=bearer(stranger))
    assert response.status_code == 404


async def _consulted_and_ended(db_session: AsyncSession, session_id) -> None:  # type: ignore[no-untyped-def]
    """Put a matched session where feedback opens: its consultation began, and it ended."""
    from datetime import UTC, datetime

    from app.features.peer_practice.models import PracticeSession

    now = datetime.now(UTC)
    await db_session.execute(
        update(PracticeSession)
        .where(PracticeSession.id == session_id)
        .values(status="ended", started_at=now, ended_at=now, current_phase="completed")
    )
    await db_session.flush()


async def test_feedback_is_refused_before_a_consultation_happened(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """A pairing still waiting on its accept window has nothing to rate."""
    a_token = await make_actor("fb0-a@example.com")
    await join(client, a_token)
    await join(client, await make_actor("fb0-b@example.com"))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    refused = await client.post(
        f"/api/v1/me/practice-sessions/{matched.id}/feedback",
        json={"would_practice_again": True},
        headers=bearer(a_token),
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "practice_feedback_not_open"


async def test_feedback_requires_would_practice_again_but_not_a_rating(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Legacy's form always required this one answer and left the star rating optional.

    A session either felt worth repeating or it did not, and that is the
    signal worth persisting even when someone declines to rate their partner.
    """
    a_token = await make_actor("fb1-a@example.com")
    b_token = await make_actor("fb1-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()
    await _consulted_and_ended(db_session, matched_id)

    # A successful request first: the test's own session inserted the match
    # directly rather than through a request, so nothing has committed it yet.
    # `override_get_session` rolls its shared session back to its savepoint on
    # any failed request, including a 422 — which would otherwise erase this
    # match before the assertions below ever see it, and expires `matched`,
    # which is why its id was read into a plain variable above rather than
    # read from the ORM object after that point.
    warm_up = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(a_token))
    assert warm_up.status_code == 200, warm_up.text

    missing_would_practice_again = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/feedback",
        json={"rating": 5},
        headers=bearer(a_token),
    )
    assert missing_would_practice_again.status_code == 422

    no_rating = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/feedback",
        json={"would_practice_again": True},
        headers=bearer(a_token),
    )
    assert no_rating.status_code == 200, no_rating.text


async def test_feedback_persists_would_practice_again(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Round-trips through the database, not just the response body."""
    from app.features.peer_practice.models import PracticeSession

    a_token = await make_actor("fb2-a@example.com")
    b_token = await make_actor("fb2-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()
    await _consulted_and_ended(db_session, matched.id)

    submitted = await client.post(
        f"/api/v1/me/practice-sessions/{matched.id}/feedback",
        json={"would_practice_again": False, "rating": 2, "comment": "Ran long."},
        headers=bearer(a_token),
    )
    assert submitted.status_code == 200, submitted.text

    stored = (
        await db_session.execute(select(PracticeSession).where(PracticeSession.id == matched.id))
    ).scalar_one()
    assert stored.would_practice_again is False
    assert stored.feedback_rating == 2
    assert stored.feedback_comment == "Ran long."


async def test_a_session_can_be_ended_once(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("m4-a@example.com")
    second_token = await make_actor("m4-b@example.com")
    await join(client, token)
    await join(client, second_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()
    await accept(client, matched.id, token)
    await accept(client, matched.id, second_token)

    url = f"/api/v1/me/practice-sessions/{matched.id}/end"
    first = await client.post(url, json={"reason": "finished"}, headers=bearer(token))
    assert first.json()["status"] == "ended"

    second = await client.post(url, json={}, headers=bearer(token))
    assert second.status_code == 409
    assert second.json()["code"] == "practice_session_ended"


async def test_ending_a_session_tells_the_partner(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The partner is still on the session screen; the end has to reach their stream."""
    from datetime import UTC, datetime

    from app.core.events import PENDING_KEY, user_topic

    token = await make_actor("end-push-a@example.com")
    partner_token = await make_actor("end-push-b@example.com")
    await join(client, token)
    await join(client, partner_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()
    await accept(client, matched.id, token)
    await accept(client, matched.id, partner_token)
    db_session.info.pop(PENDING_KEY, None)

    await service.end_session(
        db_session, matched.id, user_id=matched.doctor_user_id, reason="finished", now=datetime.now(UTC)
    )

    assert (
        user_topic(matched.patient_user_id),
        "practice.session_updated",
        {"session_id": str(matched.id)},
    ) in db_session.info[PENDING_KEY]


async def test_one_person_waiting_is_not_matched(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    await join(client, await make_actor("m5@example.com"))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    assert await service.match_waiting(db_session, exam.id) is None


async def test_leaving_a_queue_you_are_no_longer_in_says_so(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The update was guarded on `status = 'waiting'` and its row count
    ignored, so somebody the matcher had already taken was told they left."""
    import uuid
    from datetime import UTC, datetime

    from app.features.peer_practice import repository as queue_repo

    token = await make_actor("already-matched@example.com")
    entry_id = (await join(client, token))["entry_id"]
    await queue_repo.leave(db_session, uuid.UUID(entry_id), at=datetime.now(UTC))
    await db_session.commit()

    response = await client.delete(f"/api/v1/peer-practice/queue/{entry_id}", headers=bearer(token))
    assert response.status_code == 404
    assert response.json()["code"] == "queue_entry_not_found"


async def test_somebody_waiting_is_pushed_their_match(
    client: AsyncClient, streaming_client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The worst place in the product to poll, and it polled every few seconds.

    The matcher is a periodic job rather than a request, so this also proves
    the event path works from `job_session`: the test stands in for the job by
    flushing what the pairing queued, which is what that context manager does
    once its transaction commits.
    """
    import asyncio
    import json

    from app.core.events import flush_pending
    from tests.http.test_streams import frames

    doctor_token = await make_actor("stream-a@example.com")
    patient_token = await make_actor("stream-b@example.com")
    waiting = await join(client, doctor_token)
    await join(client, patient_token)

    url = f"/api/v1/peer-practice/queue/{waiting['entry_id']}/stream"
    async with streaming_client.stream("GET", url, headers=bearer(doctor_token)) as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        opening = await asyncio.wait_for(frames(lines, 2), timeout=10)
        assert json.loads(opening[1][1])["status"] == "waiting"

        exam = await ensure_exam(db_session, "sca")
        assert exam is not None
        matched = await service.match_waiting(db_session, exam.id)
        assert matched is not None
        await db_session.flush()
        await flush_pending(db_session)

        pushed = await asyncio.wait_for(frames(lines, 5), timeout=10)
        assert pushed[0][0] == "snapshot"
        status = json.loads(pushed[0][1])
        assert status["status"] == "matched"
        assert status["session_id"] == str(matched.id)
        # Matched is terminal: the client has the room and the stream closes.
        assert len(pushed) == 1


async def test_a_queue_stream_is_refused_to_somebody_elses_entry(
    client: AsyncClient, streaming_client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """It closes rather than leaking whether the entry exists."""
    import asyncio

    from tests.http.test_streams import frames

    owner = await make_actor("owner-q@example.com")
    entry = await join(client, owner)
    nosy = await make_actor("nosy-q@example.com")

    url = f"/api/v1/peer-practice/queue/{entry['entry_id']}/stream"
    async with streaming_client.stream("GET", url, headers=bearer(nosy)) as response:
        assert response.status_code == 200
        sent = await asyncio.wait_for(frames(response.aiter_lines(), 5), timeout=10)
        assert [name for name, _ in sent] == ["connected"]


async def test_a_matched_pair_can_join_their_room(
    client: AsyncClient, make_actor, db_session: AsyncSession, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    """`practice_sessions.room_name` was written from the start and nothing
    could mint a token for it, so two people were paired and had nowhere to
    meet."""
    a_token = await make_actor("v1-a@example.com")
    b_token = await make_actor("v1-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    # A successful request first, so the refusal below does not roll the
    # uncommitted match away (see `test_feedback_requires_...`).
    warm_up = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(a_token))
    assert warm_up.status_code == 200, warm_up.text

    # Not before both have accepted: one side may still decline.
    too_early = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/voice-token", headers=bearer(a_token)
    )
    assert too_early.status_code == 409
    assert too_early.json()["code"] == "practice_session_not_accepted"
    await accept(client, matched_id, a_token)
    await accept(client, matched_id, b_token)

    granted = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/voice-token", headers=bearer(a_token)
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["room"] == f"practice_{matched_id}"

    # Both may speak: there is no observer in a peer session, and no agent
    # rides in on the token — nobody dispatches a patient into a room where
    # the other doctor is playing one.
    issued = voice_tokens.issued[-1]
    assert issued["can_publish"] is True
    assert issued["agent_name"] is None


async def test_a_stranger_cannot_get_a_token_for_someone_elses_room(
    client: AsyncClient, make_actor, db_session: AsyncSession, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    await join(client, await make_actor("v2-a@example.com"))
    await join(client, await make_actor("v2-b@example.com"))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    stranger = await make_actor("v2-c@example.com")
    response = await client.post(
        f"/api/v1/me/practice-sessions/{matched.id}/voice-token", headers=bearer(stranger)
    )
    # Not found rather than forbidden: whether a session exists is not
    # something to confirm to somebody who is not in it.
    assert response.status_code == 404
    assert not voice_tokens.issued


async def test_an_ended_session_has_no_room_to_join(
    client: AsyncClient, make_actor, db_session: AsyncSession, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("v3-a@example.com")
    b_token = await make_actor("v3-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()
    await accept(client, matched.id, a_token)
    await accept(client, matched.id, b_token)
    await client.post(f"/api/v1/me/practice-sessions/{matched.id}/end", json={}, headers=bearer(a_token))

    response = await client.post(
        f"/api/v1/me/practice-sessions/{matched.id}/voice-token", headers=bearer(a_token)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "practice_session_ended"


async def test_a_lapsed_subscriber_cannot_queue(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Practising with somebody is paid access, not a free front door.

    It is a live room with a real partner in it, so it is gated on the same
    entitlement `POST /attempts` is. This had no check at all: a queue place
    and a match were available to anybody with a token, for any exam.
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from app.features.identity.models import User

    token = await make_actor("lapsed-peer@example.com")
    # Past the free trial, which a brand-new account is inside — and which this
    # route honours, so the refusal has to come from somebody the trial does
    # not cover.
    await db_session.execute(
        update(User)
        .where(User.email == "lapsed-peer@example.com")
        .values(created_at=datetime.now(UTC) - timedelta(days=30))
    )
    await db_session.flush()

    response = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
    )

    assert response.status_code == 403
    assert response.json()["code"] == "not_entitled"


async def test_somebody_on_their_free_trial_may_still_queue(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """The trial is three stations and fourteen days, and it covers this.

    Worth its own test: the gate takes a `TrialState` and `decide` skips the
    trial branch entirely when it is None, so a caller that forgot to build one
    would refuse every new account and look like a working gate.
    """
    token = await make_actor("fresh-peer@example.com")

    response = await client.post(
        "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
    )

    assert response.status_code == 201, response.text


async def _a_matched_session(client: AsyncClient, make_actor, db_session: AsyncSession, tag: str):  # type: ignore[no-untyped-def]
    a_token = await make_actor(f"{tag}-a@example.com")
    b_token = await make_actor(f"{tag}-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()
    return matched.id, a_token, b_token


async def test_an_abuse_report_is_emailed_to_support(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The retiring backend sent this straight to a support inbox. A report

    that only reached the server log was one nobody read until somebody went
    looking — this is the fix, not just a log line, which is why the
    assertion is on what got queued rather than on the 204.
    """
    session_id, a_token, _ = await _a_matched_session(client, make_actor, db_session, "abuse")

    response = await client.post(
        f"/api/v1/me/practice-sessions/{session_id}/report-abuse",
        json={"message": "They were rude throughout."},
        headers=bearer(a_token),
    )
    assert response.status_code == 204

    queued = (
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "peer_practice_abuse_report")
            )
        )
        .scalars()
        .all()
    )
    assert [m.recipient for m in queued] == ["support@osceguide.com"]
    assert queued[0].payload["reporter"] == "abuse-a@example.com"
    assert queued[0].payload["reported"] == "abuse-b@example.com"
    assert queued[0].payload["message"] == "They were rude throughout."


async def test_a_no_show_report_is_emailed_to_support(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    session_id, a_token, _ = await _a_matched_session(client, make_actor, db_session, "noshow")

    response = await client.post(
        f"/api/v1/me/practice-sessions/{session_id}/report-no-show",
        json={"message": "Never joined."},
        headers=bearer(a_token),
    )
    assert response.status_code == 204

    queued = (
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "peer_practice_no_show_report")
            )
        )
        .scalars()
        .all()
    )
    assert [m.recipient for m in queued] == ["support@osceguide.com"]
    assert queued[0].payload["reporter"] == "noshow-a@example.com"


async def test_a_stranger_cannot_report_a_session_they_are_not_in(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    session_id, _a_token, _b_token = await _a_matched_session(client, make_actor, db_session, "outsider")
    stranger = await make_actor("outsider-stranger@example.com")

    response = await client.post(
        f"/api/v1/me/practice-sessions/{session_id}/report-abuse",
        json={"message": "Not mine to report"},
        headers=bearer(stranger),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "practice_session_not_found"


# --- the accept handshake (C3) ----------------------------------------------
#
# A match is not a room yet: each side has `service.ACCEPT_WINDOW_SECONDS` to
# accept it, and a still-silent side times the pairing out.


async def test_a_pending_match_is_not_joinable_until_both_accept(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Being paired stops short of a room: presence is refused until both accept."""
    a_token = await make_actor("hs1-a@example.com")
    b_token = await make_actor("hs1-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    # A successful request first, the same way `test_feedback_requires_...`
    # above has to: the match was inserted directly through `db_session`
    # rather than a request, so nothing has committed it yet, and
    # `override_get_session` rolls its shared session back to its savepoint
    # on any failed request — which would otherwise erase it before the
    # refusal below is even reached.
    read_before = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(a_token))
    assert read_before.status_code == 200
    before_body = read_before.json()
    assert before_body["status"] == "pending_accept"
    assert before_body["my_accepted"] is False
    assert before_body["partner_accepted"] is False
    assert before_body["accept_expires_at"] is not None

    too_early = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/presence", headers=bearer(a_token)
    )
    assert too_early.status_code == 409
    assert too_early.json()["code"] == "practice_session_not_accepted"


async def test_a_pending_match_becomes_matched_once_both_accept(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("hs2-a@example.com")
    b_token = await make_actor("hs2-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    after_a = await accept(client, matched_id, a_token)
    assert after_a["status"] == "pending_accept"
    assert after_a["my_accepted"] is True
    assert after_a["partner_accepted"] is False

    after_b = await accept(client, matched_id, b_token)
    assert after_b["status"] == "matched"
    assert after_b["my_accepted"] is True
    assert after_b["partner_accepted"] is True
    assert after_b["accept_expires_at"] is None

    # Accepting again once both have is not an error — it just reads the
    # settled state back.
    again = await accept(client, matched_id, a_token)
    assert again["status"] == "matched"

    joinable = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/presence", headers=bearer(a_token)
    )
    assert joinable.status_code == 200, joinable.text


async def test_declining_a_match_ends_it_and_requeues_the_partner_who_had_accepted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("hs3-a@example.com")
    b_token = await make_actor("hs3-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    await accept(client, matched_id, a_token)

    declined = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/decline", headers=bearer(b_token)
    )
    assert declined.status_code == 200, declined.text
    decliner_body = declined.json()
    assert decliner_body["status"] == "ended"
    assert decliner_body["end_reason"] == "declined"
    # The decliner is not put back in a queue they just chose to leave.
    assert decliner_body["requeued_entry_id"] is None

    a_view = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(a_token))
    a_body = a_view.json()
    assert a_body["status"] == "ended"
    assert a_body["end_reason"] == "declined"
    assert a_body["requeued_entry_id"] is not None

    status_response = await client.get(
        f"/api/v1/peer-practice/queue/{a_body['requeued_entry_id']}", headers=bearer(a_token)
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "waiting"


async def test_declining_a_match_before_anyone_accepts_requeues_nobody(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("hs4-a@example.com")
    b_token = await make_actor("hs4-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    declined = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/decline", headers=bearer(b_token)
    )
    assert declined.status_code == 200, declined.text

    a_view = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(a_token))
    assert a_view.json()["requeued_entry_id"] is None


async def test_accepting_after_the_partner_declined_is_partner_unavailable(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("hs5-a@example.com")
    b_token = await make_actor("hs5-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    await client.post(f"/api/v1/me/practice-sessions/{matched_id}/decline", headers=bearer(b_token))

    too_late = await client.post(f"/api/v1/me/practice-sessions/{matched_id}/accept", headers=bearer(a_token))
    assert too_late.status_code == 409
    assert too_late.json()["code"] == "partner_unavailable"


async def test_declining_an_already_matched_pair_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    a_token = await make_actor("hs6-a@example.com")
    b_token = await make_actor("hs6-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    await accept(client, matched_id, a_token)
    await accept(client, matched_id, b_token)

    too_settled = await client.post(
        f"/api/v1/me/practice-sessions/{matched_id}/decline", headers=bearer(a_token)
    )
    assert too_settled.status_code == 409
    assert too_settled.json()["code"] == "practice_session_ended"


async def test_the_accept_window_timing_out_requeues_whoever_had_accepted(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Nobody has to decline for a pairing to fall through — silence times it out too."""
    from datetime import UTC, datetime

    from app.core.ports import get_clock
    from tests.support.fakes import FakeClock

    now = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)
    fake_clock = FakeClock(now)
    client._transport.app.dependency_overrides[get_clock] = lambda: fake_clock  # type: ignore[attr-defined]

    a_token = await make_actor("hs7-a@example.com")
    b_token = await make_actor("hs7-b@example.com")
    await join(client, a_token)
    await join(client, b_token)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id, now=now)
    assert matched is not None
    matched_id = matched.id
    await db_session.flush()

    # Only `a` accepts before the window closes.
    await accept(client, matched_id, a_token)

    fake_clock.advance(service.ACCEPT_WINDOW_SECONDS + 1)

    timed_out = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(a_token))
    assert timed_out.status_code == 200
    timed_out_body = timed_out.json()
    assert timed_out_body["status"] == "ended"
    assert timed_out_body["end_reason"] == "no_response"
    assert timed_out_body["requeued_entry_id"] is not None

    b_view = await client.get(f"/api/v1/me/practice-sessions/{matched_id}", headers=bearer(b_token))
    # `b` never accepted, so nothing put them back in the queue.
    assert b_view.json()["requeued_entry_id"] is None
