"""Taking a candidate's decision through the result workflow, for tests that need one settled."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.rubrics import published_feedback_version
from tests.support.tokens import bearer


async def settle_decision(
    client: AsyncClient,
    admin: str,
    *,
    org_slug: str,
    sitting_id: uuid.UUID | str,
    trainee_id: uuid.UUID | str,
    release: bool = False,
) -> str:
    """Record a pass and sign it off; release it too when asked. Returns the decision's URL."""
    decision = f"/api/v1/orgs/{org_slug}/sittings/{sitting_id}/candidates/{trainee_id}/decision"
    drafted = await client.put(
        decision,
        json={
            "assessment_outcome": "pass",
            "rationale": "Met the standard.",
            "expected_revision": 0,
        },
        headers=bearer(admin),
    )
    assert drafted.status_code == 200, drafted.text
    signed = await client.post(f"{decision}/sign-off", headers=bearer(admin))
    assert signed.status_code == 200, signed.text
    if release:
        released = await client.post(f"{decision}/release", headers=bearer(admin))
        assert released.status_code == 200, released.text
    return decision


async def seat_candidate(
    db_session: AsyncSession, org_id: uuid.UUID, sitting_id: uuid.UUID, trainee_id: uuid.UUID
) -> None:
    """Have this roster entry sit one station of the sitting, so a decision may be recorded (R-11).

    Links the roster entry to an account first if it has none, since a slot names
    its candidate by `users.id`. Call it again after relinking to another account.
    """
    from app.features.identity import repository as identity_repo
    from app.features.roster import repository as roster_repo
    from app.features.roster.models import Trainee
    from app.features.sittings.models import Circuit, Slot
    from app.features.stations.models import Station, StationVersion
    from tests.support.catalog import ensure_exam

    trainee = await db_session.get(Trainee, trainee_id)
    assert trainee is not None
    await db_session.refresh(trainee)
    user_id = trainee.user_id
    if user_id is None:
        user = await identity_repo.create_user(
            session=db_session, email=f"seat-{uuid.uuid4().hex[:8]}@example.com", name="T", password_hash=None
        )
        user_id = user.id
        await roster_repo.link_trainee_to_user(db_session, org_id, trainee_id, user_id=user_id)
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = Station(owner_kind="org", org_id=org_id, exam_id=exam.id, title="Sat")
    db_session.add(station)
    await db_session.flush()
    version = StationVersion(station_id=station.id, org_id=org_id, version=1, content={}, status="published")
    circuit = Circuit(org_id=org_id, sitting_id=sitting_id, name="Sat")
    db_session.add_all([version, circuit])
    await db_session.flush()
    db_session.add(
        Slot(
            org_id=org_id,
            circuit_id=circuit.id,
            slot_index=0,
            trainee_id=user_id,
            station_version_id=version.id,
            status="completed",
        )
    )
    await db_session.flush()


async def a_sitting_and_trainee(db_session: AsyncSession, org_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    sitting, trainee, _ = await a_sitting_and_named_trainee(db_session, org_id)
    return sitting, trainee


async def a_sitting_and_named_trainee(
    db_session: AsyncSession, org_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, str]:
    """The same fixture, but it tells you the candidate's address.

    Needed to assert who a released result is actually written to.
    """
    from app.features.roster.models import Trainee
    from app.features.sittings.models import Sitting

    version = await published_feedback_version(db_session, org_id)
    await db_session.flush()
    sitting = Sitting(org_id=org_id, name="Finals", mode="exam", rubric_version_id=version.id)
    email = f"c{uuid.uuid4().hex[:8]}@example.com"
    trainee = Trainee(org_id=org_id, email=email)
    db_session.add_all([sitting, trainee])
    await db_session.flush()
    await seat_candidate(db_session, org_id, sitting.id, trainee.id)
    return sitting.id, trainee.id, email
