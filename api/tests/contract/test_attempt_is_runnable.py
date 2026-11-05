"""An attempt created through the API can actually be run by a worker.

Every other test in `tests/contract/test_worker_routes.py` starts from a
fixture that writes `attempts.definition` directly. That made the worker
contract look proven while the only production writer of that column did not
exist: `create_attempt` never set it, nothing called `freeze_definition`, and
so `bootstrap` refused every real attempt with `attempt_not_ready`.

This test takes the path a candidate takes — create the attempt over HTTP,
then fetch it as the worker — and asserts the one thing the worker requires:
non-empty rendered instructions. Nothing here may reach into the repository to
arrange state, because arranging the state was the bug.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.entitlements import repository as ent_repo
from app.features.identity import repository as identity_repo
from app.features.stations import repository as stations_repo
from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

# The real thing: `assessment/tests/fixtures/stations/library_station_sca.json`,
# which is also what the golden prompt fixture was rendered from. Inlined
# rather than read from the sibling checkout so this test does not skip when
# the checkout is absent — `tests/contract/test_prompt_rendering.py` is what
# pins it against the engine's own copy.
STATION_CONTENT = {
    "station_id": "sca-demo-1",
    "station_name": "Chest pain in a 54-year-old",
    "patient_information": {
        "patient_biodata": "Raymond Okafor, 54, a school receptionist",
        "gender": "male",
        "opening_sentence": "I've had this tightness in my chest since this morning.",
        "persona": "Anxious but polite. Plays down the pain until asked directly.",
        "expanded_history": "Two hours of central chest tightness, worse on exertion.",
        "idea": ["Thinks it is indigestion."],
        "concerns": ["Frightened it is his heart, like his father."],
        "expectation": ["Wants something for the pain."],
        "questions": ["Is it serious, doctor?"],
        "examination_findings": "Looks uncomfortable. Pulse 92, regular.",
        "family_social_history": ["Father died of an MI at 58."],
        "past_med_history_allergies": ["No known allergies."],
    },
}


def worker_headers() -> dict[str, str]:
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


async def a_published_library_station(session: AsyncSession) -> uuid.UUID:
    """A platform library station, published, as an author would leave it."""
    author = await identity_repo.create_user(
        session, email=f"author{uuid.uuid4().hex[:8]}@example.com", name="Author", password_hash=None
    )
    exam = await ensure_exam(session, "sca")
    assert exam is not None, "the seed migration should have created the four exams"
    station = await stations_repo.create_station(
        session, None, exam_id=exam.id, title=str(STATION_CONTENT["station_name"])
    )
    version = await stations_repo.add_version(
        session, None, station_id=station.id, version=1, content=STATION_CONTENT
    )
    await stations_repo.set_version_status(
        session, None, version.id, status="published", at=NOW, by=author.id
    )
    await session.flush()
    return version.id


async def an_entitled_candidate(session: AsyncSession, make_actor, email: str) -> str:  # type: ignore[no-untyped-def]
    token = await make_actor(email)
    user = await identity_repo.user_by_email(session, email)
    assert user is not None
    exam = await ensure_exam(session, "sca")
    assert exam is not None
    await ent_repo.grant(
        session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await session.flush()
    return token


async def test_an_attempt_created_over_http_can_be_bootstrapped_by_a_worker(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The whole point of the product, asserted once.

    If this fails, no candidate can run a station, whatever else is green.
    """
    token = await an_entitled_candidate(db_session, make_actor, "runnable@example.com")
    station_version_id = await a_published_library_station(db_session)

    created = await client.post(
        "/api/v1/attempts",
        json={
            "kind": "practice",
            "exam_code": "sca",
            "station_version_id": str(station_version_id),
        },
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    attempt_id = created.json()["id"]

    boot = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert boot.status_code == 200, boot.text

    profile = boot.json()["attempt"]["definition"]["interaction_profile"]
    assert profile["instructions"].strip(), (
        "The worker refuses a job with empty instructions. The backend renders "
        "every prompt; nothing else will."
    )
    # The patient persona has to be in there, or the worker is playing nobody.
    assert "Raymond Okafor" in profile["instructions"]


async def test_the_bootstrap_still_withholds_the_evaluation_policy(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A7, re-asserted on the real path rather than on a hand-written fixture."""
    token = await an_entitled_candidate(db_session, make_actor, "nopolicy@example.com")
    station_version_id = await a_published_library_station(db_session)

    created = await client.post(
        "/api/v1/attempts",
        json={
            "kind": "practice",
            "exam_code": "sca",
            "station_version_id": str(station_version_id),
        },
        headers=bearer(token),
    )
    attempt_id = created.json()["id"]

    boot = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    definition = boot.json()["attempt"]["definition"]

    assert "evaluation_policy" not in definition or definition["evaluation_policy"] is None


# --------------------------------------------------------------------------
# The whole chain
# --------------------------------------------------------------------------


async def test_an_attempt_runs_from_creation_to_a_scored_result(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """Creation → bootstrap → chunks → transcript → marking → result.

    The plan's verification step 3, with a fake evaluator standing in for the
    LLM so it runs in CI. `tests/e2e` does the same against the real worker and
    the real model when credentials are set.

    Every step goes through the public route. The one place this reaches into
    the database is running the queued scoring job, because there is no worker
    process in a test.
    """
    from app.features.attempts.jobs import policy_for, score_attempt_now
    from app.features.attempts.models import Attempt
    from tests.support.fakes import FakeEvaluator
    from tests.support.sessions import opener_for

    token = await an_entitled_candidate(db_session, make_actor, "wholechain@example.com")
    station_version_id = await a_published_library_station(db_session)

    created = await client.post(
        "/api/v1/attempts",
        json={
            "kind": "practice",
            "exam_code": "sca",
            "station_version_id": str(station_version_id),
        },
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    attempt_id = created.json()["id"]

    # 1. The worker collects its job.
    boot = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())
    assert boot.status_code == 200, boot.text
    assert boot.json()["attempt"]["definition"]["interaction_profile"]["instructions"].strip()

    # 2. It streams the conversation as it happens.
    for seq, (role, text) in enumerate(
        [("assistant", "I've had this tightness since this morning."), ("user", "Tell me more.")]
    ):
        chunk = await client.post(
            f"/api/worker/attempts/{attempt_id}/transcript-chunks",
            json={
                "attempt_id": attempt_id,
                "message": {
                    "message_id": f"m{seq}",
                    "seq": seq,
                    "role": role,
                    "message": text,
                    "timestamp": NOW.isoformat(),
                },
            },
            headers=worker_headers(),
        )
        assert chunk.status_code == 202, chunk.text

    # 3. It delivers the finished transcript exactly once.
    done = await client.post(
        f"/api/worker/attempts/{attempt_id}/transcript",
        json={
            "attempt_id": attempt_id,
            "transcript": {
                "attempt_id": attempt_id,
                "messages": [
                    {
                        "message_id": "m0",
                        "seq": 0,
                        "role": "assistant",
                        "message": "I've had this tightness since this morning.",
                        "timestamp": NOW.isoformat(),
                    }
                ],
                "complete": True,
            },
        },
        headers=worker_headers(),
    )
    assert done.status_code in (200, 202), done.text

    # 4. Marking. The framework and policy come out of the frozen definition —
    #    if nothing was frozen, `policy_for` returns an empty framework and the
    #    job is never queued, which is exactly how this failed silently before.
    attempt = await db_session.get(Attempt, uuid.UUID(attempt_id))
    assert attempt is not None
    framework_id, policy_version = policy_for(attempt)
    assert framework_id, "no framework on the attempt means it would never be marked"

    wrote = await score_attempt_now(
        opener_for(db_session),
        uuid.UUID(attempt_id),
        evaluator=FakeEvaluator(),
        policy_version=policy_version,
        framework_id=framework_id,
        now=NOW,
    )
    assert wrote is True

    # 5. The candidate can read it.
    result = await client.get(f"/api/v1/attempts/{attempt_id}/result", headers=bearer(token))
    assert result.status_code == 200, result.text
    # A page, not one result: re-scoring under a new policy adds beside the old
    # rather than replacing it, so a candidate's history stays readable.
    results = result.json()["items"]
    assert [r["policy_version"] for r in results] == [policy_version]
    assert results[0]["framework_id"] == framework_id


async def test_a_degraded_render_is_served_but_never_frozen(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """A2, the rule both legacy backends get wrong.

    b2c and b2b freeze whatever the first bootstrap produced. When a station
    fails to resolve that is a generic patient prompt, and because it is frozen
    the candidate talks to nobody in particular for the whole session — and so
    does everyone who replays it afterwards.

    Here the session still starts, because refusing it helps nobody, but
    nothing is persisted: fix the station and the next bootstrap renders the
    real thing.
    """
    from app.features.attempts.models import Attempt
    from app.features.stations import repository as stations_repo

    token = await an_entitled_candidate(db_session, make_actor, "degraded@example.com")

    author = await identity_repo.create_user(
        session=db_session, email="hollow@example.com", name="A", password_hash=None
    )
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = await stations_repo.create_station(
        db_session, None, exam_id=exam.id, title="Unfinished station"
    )
    # Authored but never filled in: the shape is there, the patient is not.
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content={"station_name": "Unfinished"}
    )
    await stations_repo.set_version_status(
        db_session, None, version.id, status="published", at=NOW, by=author.id
    )
    await db_session.flush()

    created = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)},
        headers=bearer(token),
    )
    attempt_id = created.json()["id"]

    boot = await client.get(f"/api/worker/attempts/{attempt_id}", headers=worker_headers())

    assert boot.status_code == 200, "a degraded render is still served; the session goes ahead"
    assert boot.json()["attempt"]["definition"]["interaction_profile"]["instructions"].strip()

    await db_session.refresh(await db_session.get(Attempt, uuid.UUID(attempt_id)))  # type: ignore[arg-type]
    attempt = await db_session.get(Attempt, uuid.UUID(attempt_id))
    assert attempt is not None
    assert attempt.definition is None, (
        "a degraded render must not be frozen, or the generic prompt is pinned to this attempt forever"
    )


async def test_a_draft_station_is_refused_before_the_attempt_exists(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """T4, enforced at the door.

    `runnable_station` computed `published` and nothing read it, so a station
    somebody was still drafting would render and run for a candidate. The
    bootstrap refuses it now — and so does creation, which is the difference
    between a candidate never starting and a candidate sitting in a LiveKit
    room waiting for a patient that will never be dispatched.
    """
    from app.features.stations import repository as stations_repo

    token = await an_entitled_candidate(db_session, make_actor, "draftstation@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = await stations_repo.create_station(
        db_session, None, exam_id=exam.id, title="Still being written"
    )
    draft = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content=STATION_CONTENT
    )
    await db_session.commit()

    created = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca", "station_version_id": str(draft.id)},
        headers=bearer(token),
    )
    assert created.status_code == 409, created.text
    assert created.json()["code"] == "station_not_published"


async def test_a_station_withdrawn_after_creation_is_still_refused_at_bootstrap(
    client: AsyncClient, db_session: AsyncSession, make_actor
) -> None:  # type: ignore[no-untyped-def]
    """The second defence, which the first does not make redundant.

    Creation and bootstrap are separate requests with a candidate's attention
    span in between, so a version can be withdrawn after an attempt is created
    and before the worker asks for it. T4 has to hold at both ends.
    """
    from app.features.stations import repository as stations_repo

    token = await an_entitled_candidate(db_session, make_actor, "withdrawn@example.com")
    exam = await ensure_exam(db_session, "sca")
    assert exam is not None
    station = await stations_repo.create_station(
        db_session, None, exam_id=exam.id, title="Published, then pulled"
    )
    version = await stations_repo.add_version(
        db_session, None, station_id=station.id, version=1, content=STATION_CONTENT
    )
    author = await make_actor("withdrawing-author@example.com", platform_admin=True)
    assert author
    await stations_repo.set_version_status(db_session, None, version.id, status="published", at=NOW, by=None)
    await db_session.commit()

    created = await client.post(
        "/api/v1/attempts",
        json={"kind": "practice", "exam_code": "sca", "station_version_id": str(version.id)},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text

    await stations_repo.set_version_status(db_session, None, version.id, status="draft", at=NOW, by=None)
    await db_session.commit()

    boot = await client.get(f"/api/worker/attempts/{created.json()['id']}", headers=worker_headers())
    assert boot.status_code == 409, boot.text
    assert boot.json()["code"] == "station_not_published"
