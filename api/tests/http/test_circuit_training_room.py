"""A training circuit is a group video room: who can speak, who sees the scheme, how it closes.

Exam circuits stay as they were: the examiner subscribes only, the candidate speaks, and ending a
circuit closes its room. These tests pin both sides so one rule change cannot move the other.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import flush_after_commit_calls
from app.features.sittings import repository_run, service_floor, service_run
from app.features.sittings.models import Circuit, Sitting, SlotPeerMark
from tests.support.fakes import FakeRoomAgents, FakeVoiceTokens
from tests.support.rubrics import MINIMAL_RUBRIC, published_rubric_version
from tests.support.sittings import started_circuit
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db


@dataclass
class Room:
    admin: str
    circuit_id: str
    trainees: list[uuid.UUID]
    slots: list[str]

    def trainee(self, index: int) -> str:
        return mint_token(user_id=self.trainees[index], email=f"t{index}-{self.trainees[index]}@example.com")

    @property
    def base(self) -> str:
        return f"/api/v1/orgs/kings/circuits/{self.circuit_id}"


async def a_room(
    client: AsyncClient, make_actor, db_session: AsyncSession, *, mode: str = "training", people: int = 2
) -> Room:  # type: ignore[no-untyped-def]
    """A started circuit of `people` trainees, one station each. The first trainee has the turn."""
    run = await started_circuit(client, make_actor, db_session, mode=mode, trainees=people, stations=people)
    return Room(run.admin, run.circuit_id, run.trainees, run.slots)


async def bind_rubric(db_session: AsyncSession, room: Room, structure: dict) -> None:  # type: ignore[type-arg]
    """Point the room's sitting at a published rubric whose structure the test wrote."""
    version = await published_rubric_version(db_session, None, structure=structure)
    sitting_id = select(Circuit.sitting_id).where(Circuit.id == uuid.UUID(room.circuit_id)).scalar_subquery()
    await db_session.execute(
        update(Sitting).where(Sitting.id == sitting_id).values(rubric_version_id=version.id)
    )


async def actions(client: AsyncClient, room: Room) -> list[str]:
    """The intervention actions recorded so far, oldest first."""
    rows = (await client.get(f"{room.base}/interventions", headers=bearer(room.admin))).json()["items"]
    return sorted(item["action"] for item in rows)


async def can_join(client: AsyncClient, room: Room, index: int) -> bool:
    """Whether the trainee's portal offers them the room."""
    items = (await client.get("/api/v1/me/sittings", headers=bearer(room.trainee(index)))).json()["items"]
    return next(item for item in items if item["circuit_id"] == room.circuit_id)["can_join"]


async def join(client: AsyncClient, room: Room, index: int):  # type: ignore[no-untyped-def]
    return await client.post(
        f"/api/v1/me/circuits/{room.circuit_id}/join-token", headers=bearer(room.trainee(index))
    )


async def test_only_the_current_trainee_gets_a_microphone(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)

    assert (await join(client, room, 0)).status_code == 200
    assert voice_tokens.issued[-1]["can_publish_sources"] == ["camera", "microphone"]
    assert await can_join(client, room, 1) is True
    assert (await join(client, room, 1)).status_code == 200
    assert voice_tokens.issued[-1]["can_publish_sources"] == ["camera"]


async def test_the_supervisor_joins_with_camera_and_microphone(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)

    response = await client.post(f"{room.base}/observer-token", headers=bearer(room.admin))

    assert response.status_code == 200, response.text
    assert voice_tokens.issued[-1]["can_publish_sources"] == ["camera", "microphone"]


async def test_an_exam_candidate_and_examiner_keep_their_grants(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session, mode="exam", people=1)

    await join(client, room, 0)
    assert voice_tokens.issued[-1]["can_publish_sources"] == ["microphone"]
    assert voice_tokens.issued[-1]["can_publish"] is True
    await client.post(f"{room.base}/observer-token", headers=bearer(room.admin))
    assert voice_tokens.issued[-1]["can_publish_sources"] is None
    assert voice_tokens.issued[-1]["can_publish"] is False


async def test_opening_the_floor_lets_everyone_speak(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    agents.participants = [str(room.trainees[0]), str(room.trainees[1]), "observer-x", "agent-patient"]

    response = await client.post(f"{room.base}/floor", json={"open": True}, headers=bearer(room.admin))

    assert response.status_code == 200, response.text
    assert response.json()["open_floor"] is True
    assert agents.mic_log[-1][str(room.trainees[1])] is True
    await join(client, room, 1)
    assert voice_tokens.issued[-1]["can_publish_sources"] == ["camera", "microphone"]

    await client.post(f"{room.base}/floor", json={"open": False}, headers=bearer(room.admin))
    assert agents.mic_log[-1][str(room.trainees[1])] is False
    assert agents.mic_log[-1][str(room.trainees[0])] is True
    assert await actions(client, room) == ["floor_changed", "floor_changed"]


async def test_the_floor_and_mic_routes_are_the_supervisors_alone(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    identity = str(room.trainees[1])

    floor = await client.post(f"{room.base}/floor", json={"open": True}, headers=bearer(room.trainee(1)))
    mic = await client.post(
        f"{room.base}/participants/{identity}/mic", json={"allowed": True}, headers=bearer(room.trainee(1))
    )
    close = await client.post(f"{room.base}/room/close", headers=bearer(room.trainee(1)))

    assert (floor.status_code, mic.status_code, close.status_code) == (403, 403, 403)
    assert agents.mic_log == []


async def test_one_persons_microphone_can_be_switched(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    identity = str(room.trainees[1])

    response = await client.post(
        f"{room.base}/participants/{identity}/mic", json={"allowed": True}, headers=bearer(room.admin)
    )

    assert response.status_code == 200, response.text
    assert agents.mic_log[-1] == {identity: True}
    history = (await client.get(f"{room.base}/interventions", headers=bearer(room.admin))).json()["items"]
    assert [item["action"] for item in history] == ["mic_changed"]


async def test_the_floor_routes_refuse_an_exam_circuit(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session, mode="exam", people=1)
    identity = str(room.trainees[0])

    floor = await client.post(f"{room.base}/floor", json={"open": True}, headers=bearer(room.admin))
    mic = await client.post(
        f"{room.base}/participants/{identity}/mic", json={"allowed": True}, headers=bearer(room.admin)
    )

    assert (floor.status_code, floor.json()["code"]) == (409, "not_a_training_circuit")
    assert (mic.status_code, mic.json()["code"]) == (409, "not_a_training_circuit")
    assert agents.mic_log == []


async def test_the_mic_moves_with_the_turn(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    agents.participants = [str(room.trainees[0]), str(room.trainees[1]), "observer-x", "agent-patient"]

    jumped = await client.post(
        f"{room.base}/jump-to", json={"slot_id": room.slots[1]}, headers=bearer(room.admin)
    )

    assert jumped.status_code == 200, jumped.text
    assert agents.mic_log[-1] == {
        str(room.trainees[0]): False,
        str(room.trainees[1]): True,
        "observer-x": True,
        "agent-patient": False,
    }


async def test_the_mic_moves_when_the_clock_advances(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    agents.participants = [str(room.trainees[0]), str(room.trainees[1])]

    for _ in range(12):
        step = await client.post(f"{room.base}/advance", json={}, headers=bearer(room.admin))
        assert step.status_code == 200, step.text
        if agents.mic_log and agents.mic_log[-1][str(room.trainees[1])]:
            break

    assert agents.mic_log[-1] == {str(room.trainees[0]): False, str(room.trainees[1]): True}


async def test_the_mic_moves_when_a_station_is_redone(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    agents.participants = [str(room.trainees[0]), str(room.trainees[1])]

    redone = await client.post(
        f"{room.base}/redo-station", json={"slot_id": room.slots[1]}, headers=bearer(room.admin)
    )

    assert redone.status_code == 200, redone.text
    assert agents.mic_log[-1] == {str(room.trainees[0]): False, str(room.trainees[1]): True}


async def test_ending_a_training_circuit_keeps_the_room_until_it_is_closed(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    agents.participants = [str(room.trainees[0]), str(room.trainees[1])]

    ended = await client.post(f"{room.base}/end", headers=bearer(room.admin))

    assert ended.status_code == 200, ended.text
    assert agents.closed == []
    assert agents.mic_log[-1] == {str(room.trainees[0]): False, str(room.trainees[1]): False}
    assert (await join(client, room, 1)).status_code == 200
    assert voice_tokens.issued[-1]["can_publish_sources"] == ["camera"]
    assert (await client.post(f"{room.base}/observer-token", headers=bearer(room.admin))).status_code == 200
    early = await client.post(f"{room.base}/floor", json={"open": True}, headers=bearer(room.admin))
    assert early.status_code == 200, early.text

    closed = await client.post(f"{room.base}/room/close", headers=bearer(room.admin))

    assert closed.status_code == 200, closed.text
    assert closed.json()["room_closed_at"] is not None
    assert agents.closed == [f"circuit_{room.circuit_id}"]
    assert "room_closed" in await actions(client, room)
    assert await can_join(client, room, 1) is False
    assert (await join(client, room, 1)).json()["code"] == "circuit_not_live"
    after = await client.post(f"{room.base}/observer-token", headers=bearer(room.admin))
    assert after.json()["code"] == "circuit_not_live"


async def test_the_room_cannot_be_closed_while_the_circuit_runs(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)

    response = await client.post(f"{room.base}/room/close", headers=bearer(room.admin))

    assert (response.status_code, response.json()["code"]) == (409, "circuit_not_ended")
    assert agents.closed == []


async def test_ending_an_exam_circuit_still_shuts_its_room(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session, mode="exam", people=1)

    await client.post(f"{room.base}/end", headers=bearer(room.admin))

    assert (await join(client, room, 0)).json()["code"] == "circuit_not_live"
    assert (await client.post(f"{room.base}/observer-token", headers=bearer(room.admin))).json()["code"] == (
        "circuit_not_live"
    )
    close = await client.post(f"{room.base}/room/close", headers=bearer(room.admin))
    assert (close.status_code, close.json()["code"]) == (409, "not_a_training_circuit")


async def test_the_scheme_is_shown_to_staff_and_waiting_trainees_only(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(
        db_session,
        room,
        {**MINIMAL_RUBRIC, "sections": [{"id": "faculty", "label": "SECRET-FACULTY-NOTE", "kind": "list"}]},
    )
    waiting = f"/api/v1/me/circuits/{room.circuit_id}/scheme"

    staff = await client.get(f"{room.base}/scheme", headers=bearer(room.admin))
    other = await client.get(waiting, headers=bearer(room.trainee(1)))
    current = await client.get(waiting, headers=bearer(room.trainee(0)))
    stranger = await client.get(waiting, headers=bearer(mint_token(email="nobody@example.com")))

    assert staff.status_code == 200, staff.text
    assert other.status_code == 200, other.text
    assert staff.json()["slot_id"] == room.slots[0]
    assert [(b["block"], b["title"]) for b in staff.json()["structure"]["outline"]] == [
        ("domain", "Consulting")
    ]
    assert "SECRET-FACULTY-NOTE" not in staff.text
    assert other.json() == staff.json()
    assert (current.status_code, current.json()["code"]) == (403, "scheme_not_shown")
    assert (stranger.status_code, stranger.json()["code"]) == (404, "circuit_not_found")


async def test_an_exam_never_shows_its_scheme(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session, mode="exam", people=1)

    staff = await client.get(f"{room.base}/scheme", headers=bearer(room.admin))
    mine = await client.get(f"/api/v1/me/circuits/{room.circuit_id}/scheme", headers=bearer(room.trainee(0)))

    assert (staff.status_code, staff.json()["code"]) == (403, "scheme_not_shown")
    assert (mine.status_code, mine.json()["code"]) == (403, "scheme_not_shown")


async def test_a_tick_during_the_consultation_is_kept_and_reopens_prefilled(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    reviews = f"/api/v1/orgs/kings/slots/{room.slots[0]}/reviews"
    field = (await client.get(reviews, headers=bearer(room.admin))).json()["form"]["fields"][0]["path"]

    saved = await client.put(
        f"{reviews}/mine",
        json={"field_values": {field: "G"}, "status": "draft"},
        headers=bearer(room.admin),
    )
    reopened = await client.get(f"{reviews}/mine", headers=bearer(room.admin))

    assert saved.status_code == 200, saved.text
    assert reopened.json()["status"] == "draft"
    assert reopened.json()["field_values"][field] == "G"


async def _item(client: AsyncClient, room: Room) -> str:
    scheme = (await client.get(f"{room.base}/scheme", headers=bearer(room.admin))).json()
    domain = scheme["structure"]["outline"][0]
    return f"{domain['id']}.{domain['competencies'][0]['id']}"


def _peer(room: Room, slot: int) -> str:
    return f"/api/v1/me/circuits/{room.circuit_id}/slots/{room.slots[slot]}/peer-marks"


async def test_a_waiting_trainee_marks_the_current_turn_and_the_supervisor_sees_it(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)
    body = {"marks": [{"item": item, "rating": "G", "comment": "Warm opening"}]}

    first = await client.put(_peer(room, 0), json=body, headers=bearer(room.trainee(1)))
    again = await client.put(
        _peer(room, 0),
        json={"marks": [{"item": item, "rating": "A", "comment": None}]},
        headers=bearer(room.trainee(1)),
    )
    seen = await client.get(f"{room.base}/slots/{room.slots[0]}/peer-marks", headers=bearer(room.admin))

    assert first.status_code == 200, first.text
    assert again.status_code == 200, again.text
    rows = seen.json()["items"]
    assert [(r["item"], r["rating"], r["comment"]) for r in rows] == [(item, "A", None)]
    assert rows[0]["marker_id"] == str(room.trainees[1])


async def test_peer_marks_refuse_the_consulted_trainee_strangers_exams_and_unknown_items(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)
    body = {"marks": [{"item": item, "rating": "G"}]}

    own = await client.put(_peer(room, 0), json=body, headers=bearer(room.trainee(0)))
    outsider = bearer(mint_token(email="nobody@example.com"))
    stranger = await client.put(_peer(room, 0), json=body, headers=outsider)
    unknown = await client.put(
        _peer(room, 0), json={"marks": [{"item": "nope.nope"}]}, headers=bearer(room.trainee(1))
    )
    not_running = await client.put(_peer(room, 1), json=body, headers=bearer(room.trainee(0)))

    assert (own.status_code, own.json()["code"]) == (403, "peer_marks_own_turn")
    assert (stranger.status_code, stranger.json()["code"]) == (404, "circuit_not_found")
    assert (unknown.status_code, unknown.json()["code"]) == (409, "peer_mark_item_unknown")
    assert (not_running.status_code, not_running.json()["code"]) == (409, "peer_marks_closed")


async def test_peer_marks_are_refused_in_an_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    exam = await a_room(client, make_actor, db_session, mode="exam", people=1)

    refused = await client.put(
        _peer(exam, 0), json={"marks": [{"item": "x", "rating": "G"}]}, headers=bearer(exam.trainee(0))
    )

    assert (refused.status_code, refused.json()["code"]) == (403, "peer_marks_not_allowed")


async def test_the_consulted_trainee_reads_peer_marks_only_after_feedback_is_shared(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)
    await client.put(
        _peer(room, 0),
        json={"marks": [{"item": item, "rating": "G", "comment": "Clear"}]},
        headers=bearer(room.trainee(1)),
    )
    mine = f"/api/v1/me/slots/{room.slots[0]}/peer-marks"

    before = await client.get(mine, headers=bearer(room.trainee(0)))
    reviews = f"/api/v1/orgs/kings/slots/{room.slots[0]}/reviews"
    path = (await client.get(reviews, headers=bearer(room.admin))).json()["form"]["fields"][0]["path"]
    done = await client.put(
        f"{reviews}/mine",
        json={"field_values": {path: "G"}, "status": "completed"},
        headers=bearer(room.admin),
    )
    assert done.status_code == 200, done.text
    after = await client.get(mine, headers=bearer(room.trainee(0)))
    other = await client.get(mine, headers=bearer(room.trainee(1)))

    assert before.json()["items"] == []
    assert [(r["item"], r["rating"], r["comment"]) for r in after.json()["items"]] == [(item, "G", "Clear")]
    assert (other.status_code, other.json()["code"]) == (404, "slot_not_found")


async def _ended_at(db_session: AsyncSession, room: Room, ago: timedelta) -> datetime:
    """Backdate the circuit's end so the reaper's clock can be tested; returns the reaper's `now`."""
    now = datetime.now(UTC)
    await db_session.execute(
        update(Circuit).where(Circuit.id == uuid.UUID(room.circuit_id)).values(ended_at=now - ago)
    )
    return now


async def test_the_reaper_closes_only_a_training_room_forgotten_for_hours(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    training = await a_room(client, make_actor, db_session)
    await client.post(f"{training.base}/end", headers=bearer(training.admin))
    now = await _ended_at(db_session, training, timedelta(hours=7))
    cutoff = now - service_run.ROOM_KEPT_FOR

    due = await repository_run.forgotten_training_rooms(db_session, ended_before=cutoff)
    assert [d.circuit_id for d in due] == [uuid.UUID(training.circuit_id)]
    closed = await service_run.close_forgotten_room(
        db_session, due[0].org_id, due[0].circuit_id, agents=agents, now=now
    )

    assert closed is True
    assert agents.closed == [f"circuit_{training.circuit_id}"]
    stored = await db_session.scalar(
        select(Circuit.room_closed_at).where(Circuit.id == uuid.UUID(training.circuit_id))
    )
    assert stored is not None
    assert await repository_run.forgotten_training_rooms(db_session, ended_before=cutoff) == []


async def test_the_reaper_leaves_a_recently_ended_training_room_alone(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    recent = await a_room(client, make_actor, db_session)
    await client.post(f"{recent.base}/end", headers=bearer(recent.admin))
    now = await _ended_at(db_session, recent, timedelta(hours=1))

    assert (
        await repository_run.forgotten_training_rooms(
            db_session, ended_before=now - service_run.ROOM_KEPT_FOR
        )
        == []
    )


async def test_the_reaper_never_picks_an_exam(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    exam = await a_room(client, make_actor, db_session, mode="exam", people=1)
    await client.post(f"{exam.base}/end", headers=bearer(exam.admin))
    now = await _ended_at(db_session, exam, timedelta(hours=9))

    assert (
        await repository_run.forgotten_training_rooms(
            db_session, ended_before=now - service_run.ROOM_KEPT_FOR
        )
        == []
    )


async def test_a_request_that_rolls_back_never_moves_microphones(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    agents.participants = [str(room.trainees[0]), str(room.trainees[1])]
    before = len(agents.mic_log)
    circuit = await db_session.get(Circuit, uuid.UUID(room.circuit_id))

    await service_floor.sync_mics(db_session, circuit.org_id, circuit, agents=agents)
    assert len(agents.mic_log) == before  # queued, not applied under the request's lock
    db_session.info.pop("after_commit_calls", None)  # what a rollback leaves behind: nothing is ever run
    await flush_after_commit_calls(db_session)

    assert len(agents.mic_log) == before


async def test_the_patient_has_no_microphone_setting(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)

    response = await client.post(
        f"{room.base}/participants/agent-patient/mic", json={"allowed": False}, headers=bearer(room.admin)
    )

    assert response.status_code == 200, response.text
    assert agents.mic_log == []
    assert "mic_changed" not in await actions(client, room)


async def test_a_live_tick_cannot_undo_a_released_review(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    reviews = f"/api/v1/orgs/kings/slots/{room.slots[0]}/reviews"
    field = (await client.get(reviews, headers=bearer(room.admin))).json()["form"]["fields"][0]["path"]
    done = await client.put(
        f"{reviews}/mine",
        json={"field_values": {field: "G"}, "status": "completed"},
        headers=bearer(room.admin),
    )

    tick = await client.put(
        f"{reviews}/mine",
        json={"field_values": {field: "A"}, "status": "draft", "partial": True},
        headers=bearer(room.admin),
    )
    reread = await client.get(f"{reviews}/mine", headers=bearer(room.admin))

    assert done.status_code == 200, done.text
    assert (tick.status_code, tick.json()["code"]) == (409, "review_already_completed")
    assert (reread.json()["status"], reread.json()["field_values"][field]) == ("completed", "G")


async def test_a_live_tick_keeps_the_notes_typed_elsewhere(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    reviews = f"/api/v1/orgs/kings/slots/{room.slots[0]}/reviews"
    field = (await client.get(reviews, headers=bearer(room.admin))).json()["form"]["fields"][0]["path"]
    await client.put(
        f"{reviews}/mine",
        json={"field_values": {field: "G"}, "notes": "Kept my notes", "status": "draft"},
        headers=bearer(room.admin),
    )

    tick = await client.put(
        f"{reviews}/mine",
        json={"field_values": {field: "A"}, "status": "draft", "partial": True},
        headers=bearer(room.admin),
    )
    reread = (await client.get(f"{reviews}/mine", headers=bearer(room.admin))).json()

    assert tick.status_code == 200, tick.text
    assert (reread["notes"], reread["field_values"][field]) == ("Kept my notes", "A")


async def test_a_trainee_sees_domains_and_names_only_of_the_scheme(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(
        db_session,
        room,
        {**MINIMAL_RUBRIC, "sections": [{"id": "faculty", "label": "SECRET-FACULTY-NOTE", "kind": "list"}]},
    )

    seen = await client.get(f"/api/v1/me/circuits/{room.circuit_id}/scheme", headers=bearer(room.trainee(1)))

    for hidden in (
        "advanced",
        "competencyFeedback",
        "live",
        "instructions",
        "SECRET-FACULTY-NOTE",
        "feedback",
    ):
        assert hidden not in seen.text


async def test_redoing_a_station_clears_the_peer_marks_on_it(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)
    await client.put(
        _peer(room, 0), json={"marks": [{"item": item, "rating": "G"}]}, headers=bearer(room.trainee(1))
    )

    redone = await client.post(
        f"{room.base}/redo-station", json={"slot_id": room.slots[0]}, headers=bearer(room.admin)
    )
    seen = await client.get(f"{room.base}/slots/{room.slots[0]}/peer-marks", headers=bearer(room.admin))

    assert redone.status_code == 200, redone.text
    assert seen.json()["items"] == []


async def test_a_peer_rating_outside_met_partly_not_met_is_refused(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)

    refused = await client.put(
        _peer(room, 0), json={"marks": [{"item": item, "rating": "Z"}]}, headers=bearer(room.trainee(1))
    )

    assert (refused.status_code, refused.json()["code"]) == (409, "peer_mark_rating_unknown")


async def test_clearing_both_rating_and_comment_removes_the_peer_mark(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)
    await client.put(
        _peer(room, 0), json={"marks": [{"item": item, "rating": "G"}]}, headers=bearer(room.trainee(1))
    )

    cleared = await client.put(
        _peer(room, 0),
        json={"marks": [{"item": item, "rating": None, "comment": ""}]},
        headers=bearer(room.trainee(1)),
    )

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["items"] == []
    rows = (
        await db_session.execute(select(SlotPeerMark).where(SlotPeerMark.slot_id == uuid.UUID(room.slots[0])))
    ).all()
    assert rows == []


async def test_a_web_style_competency_key_is_accepted_and_a_trainee_cannot_read_the_org_wide_marks(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    domain = (await client.get(f"{room.base}/scheme", headers=bearer(room.admin))).json()["structure"][
        "outline"
    ][0]
    key = f"{domain['id']}.{domain['competencies'][0]['id']}"  # web `peerItem(domainId, competencyId)`

    saved = await client.put(
        _peer(room, 0), json={"marks": [{"item": key, "rating": "A"}]}, headers=bearer(room.trainee(1))
    )
    peeking = await client.get(
        f"{room.base}/slots/{room.slots[0]}/peer-marks", headers=bearer(room.trainee(1))
    )

    assert saved.status_code == 200, saved.text
    assert peeking.status_code == 403


async def test_peer_marks_are_not_readable_back_on_an_exam_slot(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    exam = await a_room(client, make_actor, db_session, mode="exam", people=1)

    mine = await client.get(f"/api/v1/me/slots/{exam.slots[0]}/peer-marks", headers=bearer(exam.trainee(0)))

    assert mine.status_code == 200
    assert mine.json()["items"] == []


async def test_an_exam_token_carries_no_display_name(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    exam = await a_room(client, make_actor, db_session, mode="exam", people=1)

    await join(client, exam, 0)

    assert voice_tokens.issued[-1]["display_name"] is None


async def test_a_training_token_carries_the_trainees_name(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    voice_tokens: FakeVoiceTokens,
    agents: FakeRoomAgents,
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)

    await join(client, room, 0)

    assert voice_tokens.issued[-1]["display_name"]


async def test_the_org_wide_peer_marks_are_the_running_staffs_alone(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    url = f"{room.base}/slots/{room.slots[0]}/peer-marks"

    supervisor = await client.get(url, headers=bearer(room.admin))
    trainee = await client.get(url, headers=bearer(room.trainee(1)))
    outsider = await client.get(url, headers=bearer(mint_token(email="elsewhere@example.com")))

    assert supervisor.status_code == 200, supervisor.text
    assert trainee.status_code == 403
    assert outsider.status_code in (403, 404)


async def test_training_tokens_last_five_minutes_and_exam_tokens_fifteen(
    client: AsyncClient, make_actor, db_session: AsyncSession, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    training = await a_room(client, make_actor, db_session)
    await join(client, training, 0)
    await client.post(f"{training.base}/observer-token", headers=bearer(training.admin))

    assert [item["ttl_seconds"] for item in voice_tokens.issued[-2:]] == [300, 300]


async def test_exam_tokens_last_fifteen_minutes_for_the_candidate_and_the_examiner(
    client: AsyncClient, make_actor, db_session: AsyncSession, voice_tokens: FakeVoiceTokens
) -> None:  # type: ignore[no-untyped-def]
    exam = await a_room(client, make_actor, db_session, mode="exam", people=1)
    await join(client, exam, 0)
    await client.post(f"{exam.base}/observer-token", headers=bearer(exam.admin))

    assert [item["ttl_seconds"] for item in voice_tokens.issued[-2:]] == [900, 900]


async def test_a_mic_or_close_call_to_livekit_runs_after_commit(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)
    circuit = await db_session.get(Circuit, uuid.UUID(room.circuit_id))
    from app.features.identity.models import User

    principal = type("P", (), {"user_id": (await db_session.scalar(select(User.id).limit(1)))})()
    now = datetime.now(UTC)

    await service_floor.set_participant_mic(
        db_session,
        circuit.org_id,
        circuit.id,
        identity=str(room.trainees[1]),
        allowed=True,
        agents=agents,
        actor=principal,
        now=now,
    )
    assert agents.mic_log == []  # queued, not run under the row lock
    await flush_after_commit_calls(db_session)
    assert agents.mic_log == [{str(room.trainees[1]): True}]


async def test_a_mic_identity_must_be_a_user_or_observer_id(
    client: AsyncClient, make_actor, db_session: AsyncSession, agents: FakeRoomAgents
) -> None:  # type: ignore[no-untyped-def]
    room = await a_room(client, make_actor, db_session)

    for bad in ("not-a-uuid", "observer-nope", "x" * 80):
        response = await client.post(
            f"{room.base}/participants/{bad}/mic", json={"allowed": True}, headers=bearer(room.admin)
        )
        assert (response.status_code, response.json()["code"]) == (422, "invalid_input"), bad
    assert agents.mic_log == []


async def test_a_revoked_trainee_cannot_read_the_scheme_or_mark_peers(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    from app.features.roster.models import Trainee

    room = await a_room(client, make_actor, db_session)
    await bind_rubric(db_session, room, MINIMAL_RUBRIC)
    item = await _item(client, room)

    async def revoke() -> None:
        # A refused request rolls the shared test session back, so the revoke is repeated for each.
        await db_session.execute(
            update(Trainee)
            .where(Trainee.user_id == room.trainees[1])
            .values(access_revoked_at=datetime.now(UTC))
        )

    await revoke()
    mine = f"/api/v1/me/circuits/{room.circuit_id}/scheme"
    scheme = await client.get(mine, headers=bearer(room.trainee(1)))
    await revoke()
    marked = await client.put(
        _peer(room, 0), json={"marks": [{"item": item, "rating": "G"}]}, headers=bearer(room.trainee(1))
    )

    assert scheme.status_code in (403, 409), scheme.text
    assert marked.status_code in (403, 409), marked.text
    assert marked.json()["code"] == scheme.json()["code"] != "scheme_not_shown"
