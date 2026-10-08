"""A peer consultation is recorded, and what was said is put through marking.

The value of peer practice is the feedback, and the feedback exists only
because the room was recorded: there is no agent in it keeping a transcript.
So what is asserted here is the chain — the recording starts when the
consultation does, stops when it ends, and becomes an attempt somebody can
actually read a mark on.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.peer_practice import repository_sessions, service, service_recording
from app.features.peer_practice.service_lifecycle import advance_phases_if_due
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeRoomRecorder, FakeTranscriber
from tests.support.library import publish_library_station
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


async def _matched(client: AsyncClient, make_actor, db_session: AsyncSession, tag: str):  # type: ignore[no-untyped-def]
    await publish_library_station(db_session, "sca")
    a_token = await make_actor(f"{tag}-a@example.com")
    b_token = await make_actor(f"{tag}-b@example.com")
    for token in (a_token, b_token):
        response = await client.post(
            "/api/v1/peer-practice/queue", json={"exam_code": "sca"}, headers=bearer(token)
        )
        assert response.status_code == 201, response.text
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    row = await service.match_waiting(db_session, exam.id)
    assert row is not None
    await db_session.flush()
    return row


async def test_the_recording_starts_when_the_consultation_does(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Not when the pair were matched: preparation is somebody reading alone."""
    row = await _matched(client, make_actor, db_session, "rec-start")
    recorder = FakeRoomRecorder()

    await service_recording.start_recording(db_session, row, exam_code="sca", recorder=recorder)
    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.recording_state == "recording"
    assert refreshed.egress_id == "EG_1"
    assert recorder.started == [(row.room_name, refreshed.recording_key)]


async def test_a_second_start_cannot_orphan_a_running_recording(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """Presence is a heartbeat, so this path is walked again and again."""
    row = await _matched(client, make_actor, db_session, "rec-twice")
    recorder = FakeRoomRecorder()

    await service_recording.start_recording(db_session, row, exam_code="sca", recorder=recorder)
    again = await repository_sessions.session_by_id(db_session, row.id)
    assert again is not None
    await service_recording.start_recording(db_session, again, exam_code="sca", recorder=recorder)

    assert len(recorder.started) == 1


async def test_a_recording_that_cannot_start_does_not_end_the_session(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The consultation is worth more than the recording of it."""
    row = await _matched(client, make_actor, db_session, "rec-fail")

    await service_recording.start_recording(
        db_session, row, exam_code="sca", recorder=FakeRoomRecorder(fail_start=True)
    )
    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.recording_state == "failed"
    assert refreshed.recording_error
    assert refreshed.status != "ended"


async def test_the_phase_machine_stops_the_recording_when_the_consultation_ends(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    row = await _matched(client, make_actor, db_session, "rec-phase")
    recorder = FakeRoomRecorder()
    await service_recording.start_recording(db_session, row, exam_code="sca", recorder=recorder)

    now = datetime.now(UTC)
    await repository_sessions.advance_phase(
        db_session,
        row.id,
        values={"current_phase": "consultation", "phase_ends_at": now - timedelta(seconds=1)},
    )
    consulting = await repository_sessions.session_by_id(db_session, row.id)
    assert consulting is not None
    await advance_phases_if_due(db_session, consulting, exam_code="sca", now=now, recorder=recorder)

    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.current_phase == "debrief"
    assert refreshed.recording_state == "stopped"
    assert recorder.stopped == ["EG_1"]


async def test_ending_early_still_stops_and_queues(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """One of the pair pressing the button is how a consultation usually ends."""
    row = await _matched(client, make_actor, db_session, "rec-early")
    recorder = FakeRoomRecorder()
    await service_recording.start_recording(db_session, row, exam_code="sca", recorder=recorder)
    started = await repository_sessions.session_by_id(db_session, row.id)
    assert started is not None

    await service_recording.stop_recording_and_queue(
        db_session, started, now=datetime.now(UTC), recorder=recorder
    )

    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.recording_state == "stopped"
    assert recorder.stopped == ["EG_1"]


async def test_an_abandoned_consultation_is_stopped_but_not_marked(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The End dialog promised no feedback; the egress must still stop, it costs money."""
    from sqlalchemy import text

    row = await _matched(client, make_actor, db_session, "rec-abandon")
    recorder = FakeRoomRecorder()
    await service_recording.start_recording(db_session, row, exam_code="sca", recorder=recorder)
    started = await repository_sessions.session_by_id(db_session, row.id)
    assert started is not None

    await service_recording.stop_recording_and_queue(
        db_session, started, now=datetime.now(UTC), mark=False, recorder=recorder
    )

    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.recording_state == "stopped"
    assert recorder.stopped == ["EG_1"]
    queued = await db_session.execute(
        text("SELECT count(*) FROM procrastinate_jobs WHERE queueing_lock LIKE :lock"),
        {"lock": f"transcribe:{row.id}:%"},
    )
    assert queued.scalar_one() == 0


async def test_only_the_doctor_is_told_where_their_feedback_is(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    """The patient is not scored, and must not be handed somebody else's attempt."""
    row = await _matched(client, make_actor, db_session, "rec-read")
    from app.features.peer_practice.service_station import session_read

    doctor_view = await session_read(db_session, row, viewer_id=row.doctor_user_id)
    patient_view = await session_read(db_session, row, viewer_id=row.patient_user_id)

    assert doctor_view.feedback_state == "none"
    assert patient_view.feedback_state == "none"
    assert patient_view.doctor_attempt_id is None


PEER_STATION = {
    "station_id": "sca-peer-1",
    "station_name": "Headache in a 31-year-old",
    "patient_information": {
        "patient_biodata": "Amara Nwosu, 31, a teacher",
        "gender": "female",
        "opening_sentence": "I've had this headache for a week now.",
        "persona": "Tired and a little worried.",
        "expanded_history": "A week of frontal headache, worse in the evenings.",
        "idea": ["Thinks it is eye strain."],
        "concerns": ["Worried about a tumour."],
        "expectation": ["Wants a scan."],
        "questions": ["Could it be something serious?"],
        "examination_findings": "Looks well. No focal neurology.",
        "family_social_history": ["Lives with her partner."],
        "past_med_history_allergies": ["No known allergies."],
    },
}


async def _a_published_station(session: AsyncSession) -> None:
    """Peer matching picks a published station; without one there is nothing to mark."""
    from app.features.stations import repository as stations_repo

    exam = await ensure_exam(session, "sca")
    assert exam is not None
    station = await stations_repo.create_station(
        session, None, exam_id=exam.id, title=str(PEER_STATION["station_name"])
    )
    version = await stations_repo.add_version(
        session, None, station_id=station.id, version=1, content=PEER_STATION
    )
    await stations_repo.set_version_status(
        session, None, version.id, status="published", at=datetime.now(UTC), by=None
    )
    # The library pick reads the station's *current* version, so publishing the
    # version alone leaves it invisible to matching.
    await stations_repo.set_current_version(session, None, station.id, version_id=version.id)
    await session.flush()


async def _entitle(session: AsyncSession, user_id) -> None:  # type: ignore[no-untyped-def]
    from app.features.entitlements import repository as ent_repo

    exam = await ensure_exam(session, "sca")
    assert exam is not None
    await ent_repo.grant(
        session,
        user_id=user_id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await session.flush()


async def _stopped(client: AsyncClient, make_actor, db_session: AsyncSession, tag: str):  # type: ignore[no-untyped-def]
    """A pair who have finished a recorded consultation."""
    await _a_published_station(db_session)
    row = await _matched(client, make_actor, db_session, tag)
    recorder = FakeRoomRecorder()
    await service_recording.start_recording(db_session, row, exam_code="sca", recorder=recorder)
    started = await repository_sessions.session_by_id(db_session, row.id)
    assert started is not None
    await service_recording.stop_recording_and_queue(
        db_session, started, now=datetime.now(UTC), recorder=recorder
    )
    stopped = await repository_sessions.session_by_id(db_session, row.id)
    assert stopped is not None
    assert stopped.station_version_id is not None, "matching should have picked the published station"
    return stopped


async def test_a_recorded_consultation_becomes_an_attempt_the_doctor_can_read(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """P-1 end to end: the whole point of recording a peer session.

    Everything past the transcript is the pipeline that already marks an AI
    mock, so what is asserted here is that a peer session arrives in it: an
    attempt of `kind='peer'` pointing back at the session, with the two
    speakers' turns stored as the doctor's transcript.
    """
    from app.features.attempts import repository as attempts_repo
    from app.features.peer_practice import service_feedback, service_station

    row = await _stopped(client, make_actor, db_session, "rec-e2e")
    await _entitle(db_session, row.doctor_user_id)
    _fake_recording_in_the_bucket(monkeypatch)
    transcriber = FakeTranscriber()

    attempt_id = await service_feedback.build_feedback(
        db_session,
        row.id,
        now=datetime.now(UTC),
        transcriber=transcriber,
        diarise=_two_turns,
    )

    assert attempt_id is not None
    attempt = await attempts_repo.attempt_by_id(db_session, attempt_id)
    assert attempt is not None
    assert attempt.kind == "peer"
    assert attempt.peer_session_id == row.id
    assert attempt.user_id == row.doctor_user_id
    assert attempt.definition is not None, "without a frozen rubric the marking refuses"
    assert transcriber.asked, "the recording should have been fetched to be transcribed"

    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    doctor_view = await service_station.session_read(db_session, refreshed, viewer_id=row.doctor_user_id)
    patient_view = await service_station.session_read(db_session, refreshed, viewer_id=row.patient_user_id)
    assert doctor_view.doctor_attempt_id == attempt_id
    assert patient_view.doctor_attempt_id is None, "the patient is not scored, and is not shown a mark"


async def test_a_transcript_that_cannot_be_recovered_is_said_plainly(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """A failure here is the end of the road: there is no second recording.

    So it is written onto the session rather than logged and forgotten — the
    screen can then say the consultation could not be marked, which is the
    only thing left that is true.
    """
    from app.features.peer_practice import service_feedback

    row = await _stopped(client, make_actor, db_session, "rec-notext")
    _fake_recording_in_the_bucket(monkeypatch)

    attempt_id = await service_feedback.build_feedback(
        db_session,
        row.id,
        now=datetime.now(UTC),
        transcriber=FakeTranscriber(fail=True),
        diarise=_two_turns,
    )

    assert attempt_id is None
    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.recording_state == "failed"
    assert refreshed.recording_error
    assert refreshed.doctor_attempt_id is None


async def test_a_recording_that_has_not_landed_yet_is_retried_not_failed(
    client: AsyncClient, make_actor, db_session: AsyncSession, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """Egress uploads after the stop is acknowledged, sometimes by a lot."""
    from app.features.peer_practice import service_feedback
    from app.features.peer_practice import service_feedback as module

    row = await _stopped(client, make_actor, db_session, "rec-late")
    monkeypatch.setattr(module.storage, "object_exists", lambda settings, key: False)

    with pytest.raises(service_feedback.RecordingNotReady):
        await service_feedback.build_feedback(
            db_session, row.id, now=datetime.now(UTC), transcriber=FakeTranscriber()
        )

    refreshed = await repository_sessions.session_by_id(db_session, row.id)
    assert refreshed is not None
    assert refreshed.recording_state == "stopped", "still waiting, not given up on"


def _fake_recording_in_the_bucket(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Stand in for S3, which no test may reach."""
    from app.features.peer_practice import service_feedback as module

    monkeypatch.setattr(module.storage, "object_exists", lambda settings, key: True)
    monkeypatch.setattr(
        module.storage, "readable_url", lambda settings, key, **kwargs: f"https://example.test/{key}"
    )


async def _two_turns(raw: str) -> list[dict[str, str]]:
    """Diarisation asks a model; the split itself is tested in tests/unit."""
    assert raw
    return [
        {"role": "doctor", "message": "What brings you in today?"},
        {"role": "patient", "message": "I've had a headache for a week."},
    ]
