"""An examiner reading the transcript of the candidate they were named to watch.

The gap this closes is not a missing screen: `GET /attempts/{id}/transcript` and
`/result` were owner-or-platform-admin, so the supervisor named on a circuit —
the person `observer-token` lets into the room to hear the consultation — could
not read a word of it afterwards. b2b's rule was
`policy.can_access_slot_feedback`: the organisation's administrator, or the
assigned staff whose id is on the circuit. This narrows it to the named one,
which is what "their candidate" means, and leaves an administrator who was not
named outside.

Staged the way an examination produces it: a circuit is started, the bell goes,
the patient is dispatched, and the dispatch is what creates the attempt.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.attempts import repository_transcript as transcripts
from app.features.attempts.models import Attempt
from app.features.identity import repository as identity_repo
from app.features.sittings import repository as sittings_repo
from app.features.tenancy import repository as tenancy_repo
from app.features.voice.service import get_room_agents
from tests.http.test_sittings_routes import (
    a_template_version,
    a_trainee,
    org_with_admin,
    published_station,
)
from tests.support.decisions import settle_decision
from tests.support.fakes import FakeRoomAgents
from tests.support.tokens import bearer, mint_token

pytestmark = pytest.mark.db

TURNS = (("user", "Hello doctor."), ("assistant", "Tell me what brought you in."))


@pytest.fixture
def agents(client: AsyncClient) -> FakeRoomAgents:
    """A patient that never reaches LiveKit. The dispatch needs one to exist."""
    fake = FakeRoomAgents()
    client._transport.app.dependency_overrides[get_room_agents] = lambda: fake  # type: ignore[attr-defined]
    return fake


async def an_examiner(db_session: AsyncSession, org_id: uuid.UUID, email: str) -> tuple[uuid.UUID, str]:
    """A real account with a real supervisor membership, and the token for it.

    The id comes back beside the token because the permission under test is
    *being named on the circuit*, and minting through `make_actor` would hide
    whose id it just minted for.
    """
    user = await identity_repo.create_user(db_session, email=email, name=email, password_hash=None)
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=user.id, role="supervisor")
    await db_session.flush()
    token = mint_token(
        user_id=user.id,
        email=email,
        memberships=(Membership(org_id=org_id, org_slug="kings", role="supervisor"),),
        active_org_slug="kings",
    )
    return user.id, token


async def a_consultation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin: str,
    *,
    examiner: uuid.UUID | None,
    mode: str = "exam",
) -> tuple[str, str, str]:
    """One candidate mid-consultation: returns their id, the circuit's, the attempt's."""
    template = await a_template_version(client, admin)
    sitting = (
        await client.post(
            "/api/v1/orgs/kings/sittings",
            json={"name": "Finals", "programme_id": str(template), "mode": mode},
            headers=bearer(admin),
        )
    ).json()
    station = await published_station(client, admin, "kings", "Sore knee")
    candidate = await a_trainee(db_session, f"cant-{uuid.uuid4().hex[:6]}@example.com")
    circuit = (
        await client.post(
            f"/api/v1/orgs/kings/sittings/{sitting['id']}/circuits",
            json={
                "name": "Room 1",
                "trainee_ids": [str(candidate)],
                "station_version_ids": [station],
                "supervisor_user_id": None if examiner is None else str(examiner),
            },
            headers=bearer(admin),
        )
    ).json()
    url = f"/api/v1/orgs/kings/circuits/{circuit['id']}"
    await client.post(f"{url}/start", headers=bearer(admin))
    # Reading, and then the bell: the dispatch is what creates the attempt.
    await client.post(f"{url}/advance", json={}, headers=bearer(admin))

    attempt_id = await db_session.scalar(
        select(Attempt.id).where(Attempt.slot_id == circuit["slots"][0]["id"], Attempt.status != "failed")
    )
    assert attempt_id is not None, "a consultation started with nothing to record it"
    return str(candidate), circuit["id"], str(attempt_id)


async def a_delivered_transcript(db_session: AsyncSession, attempt_id: str) -> None:
    """Two turns, so a read has something in it to be allowed or refused."""
    spoken = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
    for seq, (role, message) in enumerate(TURNS):
        await transcripts.add_chunk(
            db_session,
            uuid.UUID(attempt_id),
            message_id=f"m{seq}",
            seq=seq,
            role=role,
            message=message,
            spoken_at=spoken,
        )
    await transcripts.mark_transcript_complete(
        db_session, uuid.UUID(attempt_id), runtime_label="livekit", at=spoken
    )


# --- the examiner named on the circuit --------------------------------------


async def test_the_named_examiner_reads_the_transcript(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The whole point: the person who was watching may read what they heard."""
    org_id, admin = await org_with_admin(client, make_actor)
    examiner, token = await an_examiner(db_session, org_id, "watcher@kings.example")
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=examiner)
    await a_delivered_transcript(db_session, attempt_id)

    response = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(token))

    assert response.status_code == 200, response.text
    assert response.json()["complete"] is True
    assert [m["message"] for m in response.json()["messages"]] == [message for _, message in TURNS]


async def test_the_named_examiner_reads_the_marking(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The result beside the transcript: whoever may see one may see the other."""
    org_id, admin = await org_with_admin(client, make_actor)
    examiner, token = await an_examiner(db_session, org_id, "marker@kings.example")
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=examiner)
    await transcripts.save_result(
        db_session,
        uuid.UUID(attempt_id),
        framework_id="rubric-1",
        policy_version="platform-default@1",
        payload={"score": 66},
        model_used="test",
        at=datetime(2026, 9, 23, 12, 1, tzinfo=UTC),
    )

    response = await client.get(f"/api/v1/attempts/{attempt_id}/result", headers=bearer(token))

    assert response.status_code == 200, response.text
    assert [r["policy_version"] for r in response.json()["items"]] == ["platform-default@1"]


# --- who may not ------------------------------------------------------------


async def test_a_supervisor_not_named_on_that_circuit_is_refused(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """Being staff in the organisation is not the permission. This is the "no broader".

    Another supervisor of the organisation is not let in: a transcript is one
    candidate's consultation. The organisation's administrator is (below).
    """
    org_id, admin = await org_with_admin(client, make_actor)
    examiner, _ = await an_examiner(db_session, org_id, "hers@kings.example")
    outsider, token = await an_examiner(db_session, org_id, "not-hers@kings.example")
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=examiner)
    await a_delivered_transcript(db_session, attempt_id)

    response = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(token))

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "attempt_not_yours"


async def test_an_administrator_not_named_on_the_circuit_reads_it(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    org_id, admin = await org_with_admin(client, make_actor)
    examiner, _ = await an_examiner(db_session, org_id, "named@kings.example")
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=examiner)
    await a_delivered_transcript(db_session, attempt_id)

    response = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(admin))

    assert response.status_code == 200, response.text
    assert len(response.json()["messages"]) == 2


async def test_another_organisations_administrator_and_a_trainee_are_refused(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    org_id, admin = await org_with_admin(client, make_actor, "kings")
    _, guys_admin = await org_with_admin(client, make_actor, "guys")
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=None)
    await a_delivered_transcript(db_session, attempt_id)
    trainee = await identity_repo.create_user(
        db_session, email="trainee@kings.example", name="T", password_hash=None
    )
    await tenancy_repo.add_membership(db_session, org_id=org_id, user_id=trainee.id, role="trainee")
    await db_session.flush()
    trainee_token = mint_token(
        user_id=trainee.id,
        email="trainee@kings.example",
        memberships=(Membership(org_id=org_id, org_slug="kings", role="trainee"),),
        active_org_slug="kings",
    )
    url = f"/api/v1/attempts/{attempt_id}/transcript"

    other = await client.get(url, headers=bearer(guys_admin))
    as_trainee = await client.get(url, headers=bearer(trainee_token))

    assert other.status_code == 403, other.text
    assert as_trainee.status_code == 403, as_trainee.text


async def test_another_organisations_examiner_is_refused(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """An examiner from elsewhere cannot reach in, and cannot be named into it either.

    Naming somebody who is not this organisation's staff is refused when the circuit is
    built (R-38), and a read from the other organisation is refused as well.
    """
    _, kings = await org_with_admin(client, make_actor, "kings")
    guys_id, _ = await org_with_admin(client, make_actor, "guys")
    outsider, token = await an_examiner(db_session, guys_id, "guys-watcher@guys.example")
    _, _, attempt_id = await a_consultation(client, db_session, kings, examiner=None)
    await a_delivered_transcript(db_session, attempt_id)

    named_elsewhere = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(token))

    assert named_elsewhere.status_code == 403, named_elsewhere.text
    assert named_elsewhere.json()["code"] == "attempt_not_yours"
    assert outsider


async def test_moving_the_name_moves_the_read(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """The name on the circuit *is* the permission, so taking it away ends the access.

    Written on the row rather than through the circuit editor, because by this
    point the candidate has been dispatched and a structural edit is refused for
    its own reasons. What is being tested is who can read afterwards — and the
    allowed read comes first, because a refused one rolls the transaction back
    and would otherwise undo the very change being tested.
    """
    org_id, admin = await org_with_admin(client, make_actor)
    was, was_token = await an_examiner(db_session, org_id, "was@kings.example")
    now, now_token = await an_examiner(db_session, org_id, "now@kings.example")
    _, circuit_id, attempt_id = await a_consultation(client, db_session, admin, examiner=was)
    await a_delivered_transcript(db_session, attempt_id)
    await sittings_repo.update_circuit(db_session, org_id, uuid.UUID(circuit_id), supervisor_user_id=now)

    allowed = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(now_token))
    refused = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(was_token))

    assert allowed.status_code == 200, allowed.text
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "attempt_not_yours"


# --- the candidate, unchanged -----------------------------------------------


async def test_the_candidate_still_reads_their_own_transcript(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """A training slot is practice: the person who spoke the words reads them at once."""
    org_id, admin = await org_with_admin(client, make_actor)
    examiner, _ = await an_examiner(db_session, org_id, "watched@kings.example")
    candidate, _, attempt_id = await a_consultation(
        client, db_session, admin, examiner=examiner, mode="training"
    )
    await a_delivered_transcript(db_session, attempt_id)

    response = await client.get(
        f"/api/v1/attempts/{attempt_id}/transcript",
        headers=bearer(mint_token(user_id=uuid.UUID(candidate), email="candidate@example.com")),
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["messages"]) == 2


async def test_an_exam_candidate_reads_nothing_of_their_slot_until_release(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """R-1: the transcript and marks feed the decision, so the candidate sees them with it.

    Before release the portal links no attempt and each read is refused; once the
    decision is released, both open.
    """
    from app.features.roster import repository as roster_repo

    org_id, admin = await org_with_admin(client, make_actor)
    candidate, _, attempt_id = await a_consultation(client, db_session, admin, examiner=None)
    await a_delivered_transcript(db_session, attempt_id)
    as_candidate = bearer(mint_token(user_id=uuid.UUID(candidate), email="candidate@example.com"))

    portal = (await client.get("/api/v1/me/sittings", headers=as_candidate)).json()
    assert portal["items"][0]["slots"][0]["attempt_id"] is None
    assert portal["items"][0]["released"] is False
    for read in ("transcript", "result", "feedback"):
        refused = await client.get(f"/api/v1/attempts/{attempt_id}/{read}", headers=as_candidate)
        assert refused.status_code == 404, (read, refused.text)
        assert refused.json()["code"] == "result_not_released"

    trainee_id = (await roster_repo.trainee_ids_for_user(db_session, uuid.UUID(candidate)))[0]
    await settle_decision(
        client,
        admin,
        org_slug="kings",
        sitting_id=portal["items"][0]["id"],
        trainee_id=trainee_id,
        release=True,
    )

    portal = (await client.get("/api/v1/me/sittings", headers=as_candidate)).json()
    assert portal["items"][0]["slots"][0]["attempt_id"] == attempt_id
    assert portal["items"][0]["released"] is True
    response = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=as_candidate)
    assert response.status_code == 200, response.text
    assert len(response.json()["messages"]) == 2


async def test_a_circuit_with_no_examiner_named_gives_nobody_a_second_read(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """No name on the circuit, no second reader — a supervisor or not."""
    org_id, admin = await org_with_admin(client, make_actor)
    stranger, token = await an_examiner(db_session, org_id, "not-named@kings.example")
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=None)
    await a_delivered_transcript(db_session, attempt_id)

    response = await client.get(f"/api/v1/attempts/{attempt_id}/transcript", headers=bearer(token))

    assert response.status_code == 403, response.text


async def test_nobody_signed_in_reads_nothing(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    _, admin = await org_with_admin(client, make_actor)
    _, _, attempt_id = await a_consultation(client, db_session, admin, examiner=None)

    response = await client.get(f"/api/v1/attempts/{attempt_id}/transcript")

    assert response.status_code == 401


async def test_a_trainee_sees_a_failed_station_as_not_marked_with_no_transcript(
    client: AsyncClient,
    make_actor,
    db_session: AsyncSession,
    agents: FakeRoomAgents,  # type: ignore[no-untyped-def]
) -> None:
    """T-3: a slot whose only attempt failed says marking failed, and links no attempt."""
    from sqlalchemy import update

    from app.features.attempts.models import Attempt

    org_id, admin = await org_with_admin(client, make_actor)
    candidate, _, attempt_id = await a_consultation(client, db_session, admin, examiner=None)
    as_candidate = bearer(mint_token(user_id=uuid.UUID(candidate), email="candidate@example.com"))
    before = (await client.get("/api/v1/me/sittings", headers=as_candidate)).json()
    assert before["items"][0]["slots"][0]["marking_failed"] is False

    await db_session.execute(
        update(Attempt)
        .where(Attempt.id == uuid.UUID(attempt_id))
        .values(status="failed", failed_reason="empty_transcript")
    )
    await db_session.flush()

    slot = (await client.get("/api/v1/me/sittings", headers=as_candidate)).json()["items"][0]["slots"][0]
    assert slot["marking_failed"] is True
    assert slot["attempt_id"] is None
