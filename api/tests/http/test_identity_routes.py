"""The identity contract: status codes and error codes, not messages.

The frontend switches on `code`. b2b's client flattens errors to a bare string
and then matches English prose to decide whether to retry — these tests exist
so the replacement never needs to.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.catalog import ensure_exam
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

REGISTER = {"email": "new@example.com", "name": "New Person", "password": "correct horse battery"}


async def register(client: AsyncClient, **overrides: object) -> object:
    return await client.post("/api/v1/auth/register", json={**REGISTER, **overrides})


async def test_registering_returns_the_user_and_a_token_pair(client: AsyncClient) -> None:
    response = await register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["access_token"] and body["refresh_token"]
    # The secret itself and its hash, not the substring: `must_change_password`
    # is a legitimate field whose name contains "password".
    assert REGISTER["password"] not in str(body)
    assert "password_hash" not in str(body)


async def test_registering_twice_is_a_conflict(client: AsyncClient) -> None:
    await register(client)
    response = await register(client, name="Impostor")
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_the_same_address_in_another_casing_is_the_same_person(client: AsyncClient) -> None:
    await register(client)
    response = await register(client, email="NEW@Example.com")
    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_a_weak_password_is_refused_with_a_reason(client: AsyncClient) -> None:
    response = await register(client, password="short")
    assert response.status_code == 422
    assert response.json()["code"] == "weak_password"


async def test_signing_in_returns_a_token_pair(client: AsyncClient) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "new@example.com", "password": REGISTER["password"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_a_wrong_password_is_refused_without_saying_which_part_was_wrong(
    client: AsyncClient,
) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "new@example.com", "password": "wrong password here"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_an_unknown_address_gives_the_same_answer_as_a_wrong_password(
    client: AsyncClient,
) -> None:
    """Different codes here would turn login into an account-enumeration oracle."""
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "whatever it is"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_a_refresh_token_can_be_exchanged(client: AsyncClient) -> None:
    refresh = (await register(client)).json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert response.json()["refresh_token"] != refresh, "the refresh token must rotate"


async def test_reusing_a_rotated_refresh_token_kills_the_session(client: AsyncClient) -> None:
    """Reuse means it leaked, so the chain dies and the freshly rotated token
    the thief might hold dies with it."""
    first = (await register(client)).json()["refresh_token"]
    second = (await client.post("/api/v1/auth/refresh", json={"refresh_token": first})).json()[
        "refresh_token"
    ]

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401
    assert replay.json()["code"] == "invalid_refresh_token"

    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert after.status_code == 401, "the whole chain should be revoked, not just the replayed token"


async def test_logging_out_stops_the_refresh_token(client: AsyncClient) -> None:
    body = (await register(client)).json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 204
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert response.status_code == 401


async def test_me_returns_the_caller(client: AsyncClient) -> None:
    token = (await register(client)).json()["access_token"]
    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"
    assert response.json()["memberships"] == []


async def test_me_without_a_token_is_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


async def test_password_reset_never_reveals_whether_an_address_exists(client: AsyncClient) -> None:
    await register(client)
    known = await client.post("/api/v1/auth/password-reset", json={"email": "new@example.com"})
    unknown = await client.post("/api/v1/auth/password-reset", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


async def test_a_password_reset_queues_its_email(client: AsyncClient, db_session) -> None:  # type: ignore[no-untyped-def]
    """Queued in the same transaction as the token that makes it valid, so a
    reset that rolled back cannot leave an email promising one."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    await register(client)
    await client.post("/api/v1/auth/password-reset", json={"email": "new@example.com"})

    queued = list(
        (
            await db_session.execute(
                select(OutboundMessage).where(OutboundMessage.template_key == "password_reset")
            )
        ).scalars()
    )
    assert len(queued) == 1
    assert queued[0].recipient == "new@example.com"


async def test_an_unknown_address_queues_nothing(client: AsyncClient, db_session) -> None:  # type: ignore[no-untyped-def]
    """Same 202 either way, but no email to an address we do not hold."""
    from sqlalchemy import select

    from app.features.notifications.models import OutboundMessage

    await client.post("/api/v1/auth/password-reset", json={"email": "ghost@example.com"})
    queued = list((await db_session.execute(select(OutboundMessage))).scalars())
    assert queued == []


async def test_a_person_may_set_their_exam_date_and_reading_arrangement(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    """Fields the ported settings screens needed and had nowhere to read: an exam date with an
    optional time, and the custom timers gated by `needs_extra_time` (A3/A4)."""
    token = await make_actor("amara@example.com")

    saved = await client.patch(
        "/api/v1/me",
        json={
            "exam_date": "2026-11-03",
            "exam_time": "09:30:00",
            "needs_extra_time": True,
            "custom_reading_seconds": 90,
            "custom_simulation_seconds": 480,
        },
        headers=bearer(token),
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["exam_date"] == "2026-11-03"
    assert body["exam_time"] == "09:30:00"
    assert body["needs_extra_time"] is True
    assert body["custom_reading_seconds"] == 90
    assert body["custom_simulation_seconds"] == 480

    # A PATCH writes only what it was sent.
    renamed = await client.patch("/api/v1/me", json={"name": "Amara O."}, headers=bearer(token))
    assert renamed.json()["name"] == "Amara O."
    assert renamed.json()["exam_date"] == "2026-11-03"
    assert renamed.json()["custom_reading_seconds"] == 90

    # Clearing just the timer is distinguishable from "not mentioned", and the
    # gate can be turned off without losing the other timer's value.
    cleared_one_timer = await client.patch(
        "/api/v1/me",
        json={"custom_reading_seconds": None, "needs_extra_time": False},
        headers=bearer(token),
    )
    assert cleared_one_timer.json()["custom_reading_seconds"] is None
    assert cleared_one_timer.json()["custom_simulation_seconds"] == 480
    assert cleared_one_timer.json()["needs_extra_time"] is False

    # Clearing the exam date also clears the exam time: a time with no date
    # names nothing.
    cleared_exam = await client.patch("/api/v1/me", json={"exam_date": None}, headers=bearer(token))
    assert cleared_exam.json()["exam_date"] is None
    assert cleared_exam.json()["exam_time"] is None


async def test_an_impossible_reading_arrangement_is_refused(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
) -> None:
    """The legacy modal's own ceiling: 60 minutes 59 seconds, never zero."""
    token = await make_actor("amara@example.com")
    for bad in (0, -10, 3660, 9999):
        refused = await client.patch(
            "/api/v1/me", json={"custom_reading_seconds": bad}, headers=bearer(token)
        )
        assert refused.status_code == 422, refused.text


async def test_registering_records_the_exam_the_account_is_for(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The per-exam landing pages carry it into the form.

    This is what replaces the retiring client's per-exam subdomains: on one
    domain there is nothing in the request to say which exam somebody came to
    sit, and a trial account holds no entitlement to infer it from.
    """
    await ensure_exam(db_session, "plab")

    response = await register(client, exam_code="plab")

    assert response.status_code == 201
    assert response.json()["user"]["exam_code"] == "plab"


async def test_registering_without_an_exam_is_allowed(client: AsyncClient) -> None:
    """Somebody who arrives at the site root, and an institution's member, sign up
    without one. The web asks the first time the account opens the app."""
    response = await register(client)

    assert response.status_code == 201
    assert response.json()["user"]["exam_code"] is None


async def test_an_unknown_exam_at_sign_up_is_dropped_not_refused(client: AsyncClient) -> None:
    """A stale landing-page link must not cost somebody their sign-up. Stored, the
    code would open the account on nothing and skip the step that asks for an
    exam, so it is dropped and they are asked instead."""
    response = await register(client, exam_code="mrcp")

    assert response.status_code == 201
    assert response.json()["user"]["exam_code"] is None


async def test_an_account_without_an_exam_chooses_one_once(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An SCA account could move itself to PLAB with one PATCH, while the Exam tab
    told it that only support could. Choosing is allowed once, from nothing."""
    await ensure_exam(db_session, "sca")
    await ensure_exam(db_session, "plab")
    token = (await register(client)).json()["access_token"]

    chosen = await client.patch("/api/v1/me", json={"exam_code": "sca"}, headers=bearer(token))
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["exam_code"] == "sca"

    # Re-sending the exam they have is not a change, so a whole-profile save still works.
    unchanged = await client.patch("/api/v1/me", json={"exam_code": "sca"}, headers=bearer(token))
    assert unchanged.status_code == 200, unchanged.text

    switched = await client.patch("/api/v1/me", json={"exam_code": "plab"}, headers=bearer(token))
    assert switched.status_code == 409
    assert switched.json()["code"] == "exam_already_chosen"

    me = await client.get("/api/v1/me", headers=bearer(token))
    assert me.json()["exam_code"] == "sca"


async def test_an_exam_nobody_publishes_cannot_be_chosen(client: AsyncClient) -> None:
    token = (await register(client)).json()["access_token"]

    response = await client.patch("/api/v1/me", json={"exam_code": "mrcp"}, headers=bearer(token))

    assert response.status_code == 404
    assert response.json()["code"] == "unknown_exam"


async def test_changing_one_field_leaves_the_exam_alone(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """`model_fields_set`, not the whole body: a screen that edits a name must
    not silently clear which exam somebody is sitting."""
    await ensure_exam(db_session, "sca")
    created = await register(client, exam_code="sca")
    token = created.json()["access_token"]

    response = await client.patch("/api/v1/me", json={"name": "Renamed"}, headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["exam_code"] == "sca"
