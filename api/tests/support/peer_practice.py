"""A matched, recorded and stopped peer consultation, for tests that need one."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.peer_practice import repository_sessions, service, service_recording
from tests.support.catalog import ensure_exam
from tests.support.fakes import FakeRoomRecorder
from tests.support.library import publish_library_station
from tests.support.tokens import bearer

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


async def matched_pair(client: AsyncClient, make_actor, db_session: AsyncSession, tag: str):
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


async def published_peer_station(session: AsyncSession) -> None:
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


async def stopped_pair(client: AsyncClient, make_actor, db_session: AsyncSession, tag: str):
    """A pair who have finished a recorded consultation."""
    await published_peer_station(db_session)
    row = await matched_pair(client, make_actor, db_session, tag)
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
