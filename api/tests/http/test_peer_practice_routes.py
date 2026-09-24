"""Queueing, matching and practising."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
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


async def test_a_session_can_be_ended_once(client: AsyncClient, make_actor, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("m4-a@example.com")
    await join(client, token)
    await join(client, await make_actor("m4-b@example.com"))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()

    url = f"/api/v1/me/practice-sessions/{matched.id}/end"
    first = await client.post(url, json={"reason": "finished"}, headers=bearer(token))
    assert first.json()["status"] == "ended"

    second = await client.post(url, json={}, headers=bearer(token))
    assert second.status_code == 409
    assert second.json()["code"] == "practice_session_ended"


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
    await db_session.flush()

    granted = await client.post(
        f"/api/v1/me/practice-sessions/{matched.id}/voice-token", headers=bearer(a_token)
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["room"] == f"practice_{matched.id}"

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
    await join(client, a_token)
    await join(client, await make_actor("v3-b@example.com"))
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    matched = await service.match_waiting(db_session, exam.id)
    assert matched is not None
    await db_session.flush()
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
