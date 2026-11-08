"""GET /auth/invitation/{token}: the organisation that sent an invitation, its type and the role on offer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.features.identity.models import PasswordResetToken
from app.features.identity.tokens import hash_token
from app.features.notifications.models import OutboundMessage
from app.features.tenancy.models import Membership as MembershipRow
from tests.http.test_invitations import provisioned
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

REFUSED = {"code": "invalid_reset_token"}


class _CountingRedis:
    """The limiter's Redis, counting in memory (shared across instances for one test)."""

    counts: dict[str, int] = {}

    async def eval(self, script: str, numkeys: int, key: str, window: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def ttl(self, key: str) -> int:
        return 60


async def _invite(client: AsyncClient, make_actor, db_session: AsyncSession) -> str:  # type: ignore[no-untyped-def]
    root, _ = await provisioned(client, make_actor)
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "new.dean@ashford.ac.uk", "role": "owner"},
        headers=bearer(root),
    )
    assert seated.status_code == 201, seated.text
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
    return str((await db_session.execute(stmt)).scalars().one().payload["token"])


async def test_a_live_invitation_names_its_organisation_type_and_role(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    token = await _invite(client, make_actor, db_session)
    found = await client.get(f"/api/v1/auth/invitation/{token}")
    assert found.status_code == 200, found.text
    assert found.json() == {
        "organisation_name": "Ashford Medical School",
        "org_type": "institution",
        "role": "owner",
    }


async def test_every_other_token_gets_the_same_refusal(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    token = await _invite(client, make_actor, db_session)
    unknown = await client.get("/api/v1/auth/invitation/not-a-token")

    await db_session.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(token))
        .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    await db_session.commit()
    expired = await client.get(f"/api/v1/auth/invitation/{token}")

    await db_session.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(token))
        .values(expires_at=datetime.now(UTC) + timedelta(days=1), used_at=datetime.now(UTC))
    )
    await db_session.commit()
    spent = await client.get(f"/api/v1/auth/invitation/{token}")

    assert unknown.status_code == expired.status_code == spent.status_code == 422
    bodies = [{k: v for k, v in r.json().items() if k != "request_id"} for r in (unknown, expired, spent)]
    assert bodies[0] == bodies[1] == bodies[2]
    assert unknown.json()["code"] == "invalid_reset_token"
    assert "Ashford" not in unknown.text + expired.text + spent.text


async def test_an_ordinary_password_reset_token_is_refused(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    """A reset link carries no organisation, so the lookup cannot be used to probe reset tokens."""
    await make_actor("someone@example.com")
    sent = await client.post("/api/v1/auth/password-reset", json={"email": "someone@example.com"})
    assert sent.status_code == 202
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "password_reset")
    token = (await db_session.execute(stmt)).scalars().one().payload["token"]
    refused = await client.get(f"/api/v1/auth/invitation/{token}")
    assert refused.status_code == 422
    assert refused.json()["code"] == "invalid_reset_token"


async def test_a_reissued_invitation_still_names_the_organisation(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    root, _ = await provisioned(client, make_actor)
    seated = await client.post(
        "/api/v1/platform/organizations/ashford/memberships",
        json={"email": "new.dean@ashford.ac.uk", "role": "owner"},
        headers=bearer(root),
    )
    resent = await client.post(
        f"/api/v1/platform/organizations/ashford/memberships/{seated.json()['id']}/resend-invitation",
        headers=bearer(root),
    )
    assert resent.status_code in (200, 202), resent.text
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
    tokens = [m.payload["token"] for m in (await db_session.execute(stmt)).scalars()]
    assert len(tokens) == 2
    names = [(await client.get(f"/api/v1/auth/invitation/{t}")).json() for t in tokens]
    assert {
        "organisation_name": "Ashford Medical School",
        "org_type": "institution",
        "role": "owner",
    } in names


async def _owner_and_invite(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession, *, path: str, body: dict[str, str]
) -> tuple[str, str, dict[str, object]]:
    """An org owner invites a stranger; returns the owner's token, the invitation token and the 201 body."""
    _, org_id = await provisioned(client, make_actor)
    owner = await make_actor(
        "owner@ashford.ac.uk",
        memberships=(Membership(org_id=org_id, org_slug="ashford", role="owner"),),
        active_org_slug="ashford",
    )
    added = await client.post(path, json=body, headers=bearer(owner))
    assert added.status_code == 201, added.text
    stmt = select(OutboundMessage).where(OutboundMessage.template_key == "invitation")
    token = str((await db_session.execute(stmt)).scalars().one().payload["token"])
    return owner, token, added.json()


async def test_a_supervisor_invitation_names_the_supervisor_role(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    _, token, _ = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "tutor@ashford.ac.uk", "role": "supervisor"},
    )
    found = await client.get(f"/api/v1/auth/invitation/{token}")
    assert found.status_code == 200, found.text
    assert found.json() == {
        "organisation_name": "Ashford Medical School",
        "org_type": "institution",
        "role": "supervisor",
    }


async def test_a_roster_invitation_names_the_trainee_role(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    _, token, _ = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/trainees",
        body={"email": "stu@ashford.ac.uk"},
    )
    found = await client.get(f"/api/v1/auth/invitation/{token}")
    assert found.status_code == 200, found.text
    assert found.json() == {
        "organisation_name": "Ashford Medical School",
        "org_type": "institution",
        "role": "trainee",
    }


async def test_a_revoked_membership_spends_its_invitation_for_lookup_and_confirm(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, token, added = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "tutor@ashford.ac.uk", "role": "supervisor"},
    )
    revoked = await client.post(
        f"/api/v1/orgs/ashford/memberships/{added['id']}/revoke", headers=bearer(owner)
    )
    assert revoked.status_code == 200, revoked.text
    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "Chosen-Passw0rd!"}
    )
    assert confirmed.status_code == 422
    assert confirmed.json()["code"] == "invalid_reset_token"
    signed_in = await client.post(
        "/api/v1/auth/login", json={"email": "tutor@ashford.ac.uk", "password": "Chosen-Passw0rd!"}
    )
    assert signed_in.status_code == 401
    unknown = await client.get("/api/v1/auth/invitation/not-a-token")
    refused = await client.get(f"/api/v1/auth/invitation/{token}")
    assert refused.status_code == unknown.status_code == 422

    def strip(r):  # type: ignore[no-untyped-def]
        return {k: v for k, v in r.json().items() if k != "request_id"}

    assert strip(refused) == strip(unknown)
    assert refused.json()["code"] == "invalid_reset_token"


async def test_removing_a_trainee_spends_their_invitation(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, token, added = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/trainees",
        body={"email": "stu@ashford.ac.uk"},
    )
    revoked = await client.post(
        f"/api/v1/orgs/ashford/trainees/{added['id']}/access", json={"revoked": True}, headers=bearer(owner)
    )
    assert revoked.status_code == 200, revoked.text
    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "Chosen-Passw0rd!"}
    )
    assert confirmed.status_code == 422
    assert confirmed.json()["code"] == "invalid_reset_token"
    assert (await client.get(f"/api/v1/auth/invitation/{token}")).status_code == 422


async def _tokens_for(db_session: AsyncSession) -> list[PasswordResetToken]:
    db_session.expire_all()
    return list((await db_session.execute(select(PasswordResetToken))).scalars())


async def test_resending_to_a_revoked_seat_is_refused_and_the_old_link_stays_dead(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, token, added = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "tutor@ashford.ac.uk", "role": "supervisor"},
    )
    base = f"/api/v1/orgs/ashford/memberships/{added['id']}"
    assert (await client.post(f"{base}/revoke", headers=bearer(owner))).status_code == 200
    resent = await client.post(f"{base}/resend-invitation", headers=bearer(owner))
    assert resent.status_code == 409, resent.text
    assert resent.json()["code"] == "invitation_not_pending"
    bulk = await client.post(
        "/api/v1/orgs/ashford/memberships/bulk/resend-invitation",
        json={"membership_ids": [added["id"]]},
        headers=bearer(owner),
    )
    assert bulk.json()["results"] == [{"membership_id": added["id"], "outcome": "revoked"}]
    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "Chosen-Passw0rd!"}
    )
    assert confirmed.status_code == 422
    assert all(row.used_at is not None for row in await _tokens_for(db_session))
    assert (
        len(
            [
                m
                for m in (await db_session.execute(select(OutboundMessage))).scalars()
                if m.template_key == "invitation"
            ]
        )
        == 1
    )


async def test_resending_to_a_removed_trainee_is_refused(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, token, added = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/trainees",
        body={"email": "stu@ashford.ac.uk"},
    )
    base = f"/api/v1/orgs/ashford/trainees/{added['id']}"
    assert (
        await client.post(f"{base}/access", json={"revoked": True}, headers=bearer(owner))
    ).status_code == 200
    resent = await client.post(f"{base}/resend-invitation", headers=bearer(owner))
    assert resent.status_code == 409, resent.text
    assert resent.json()["code"] == "invitation_not_pending"
    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "password": "Chosen-Passw0rd!"}
    )
    assert confirmed.status_code == 422
    assert all(row.used_at is not None for row in await _tokens_for(db_session))


async def test_losing_one_of_two_seats_keeps_the_invitation_working(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, _, first = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "both@ashford.ac.uk", "role": "supervisor"},
    )
    second = await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "both@ashford.ac.uk", "role": "trainee"},
        headers=bearer(owner),
    )
    assert second.status_code == 201, second.text
    live = [row for row in await _tokens_for(db_session) if row.used_at is None]
    assert len(live) == 1
    revoked = await client.post(
        f"/api/v1/orgs/ashford/memberships/{second.json()['id']}/revoke", headers=bearer(owner)
    )
    assert revoked.status_code == 200, revoked.text
    assert first["id"] != second.json()["id"]
    assert [row.used_at for row in await _tokens_for(db_session) if row.id == live[0].id] == [None]
    messages = (await db_session.execute(select(OutboundMessage))).scalars()
    token = [m.payload["token"] for m in messages if m.template_key == "invitation"][-1]
    found = await client.get(f"/api/v1/auth/invitation/{token}")
    assert found.status_code == 200, found.text
    assert found.json()["role"] == "supervisor"


async def test_a_revoke_spends_only_that_organisations_tokens(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, _, added = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "tutor@ashford.ac.uk", "role": "supervisor"},
    )
    _, other_org = await provisioned(client, make_actor, slug="bexley")
    user_id = (await _tokens_for(db_session))[0].user_id
    soon = datetime.now(UTC) + timedelta(days=1)
    db_session.add_all(
        [
            PasswordResetToken(
                user_id=user_id, token_hash=hash_token("org-b"), expires_at=soon, organization_id=other_org
            ),
            PasswordResetToken(user_id=user_id, token_hash=hash_token("plain"), expires_at=soon),
        ]
    )
    await db_session.commit()
    revoked = await client.post(
        f"/api/v1/orgs/ashford/memberships/{added['id']}/revoke", headers=bearer(owner)
    )
    assert revoked.status_code == 200, revoked.text
    used = {row.token_hash: row.used_at is not None for row in await _tokens_for(db_session)}
    assert used[hash_token("org-b")] is False
    assert used[hash_token("plain")] is False
    assert sorted(used.values()) == [False, False, True]


async def test_the_lookup_is_rate_limited(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _CountingRedis.counts = {}
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: _CountingRedis())
    statuses = [(await client.get("/api/v1/auth/invitation/guess")).status_code for _ in range(21)]
    assert statuses[:20] == [422] * 20
    assert statuses[20] == 429


async def _token_for(db_session: AsyncSession, email: str, *, newest: bool = True) -> str:
    stmt = (
        select(OutboundMessage).where(OutboundMessage.recipient == email).order_by(OutboundMessage.created_at)
    )
    tokens = [m.payload["token"] for m in (await db_session.execute(stmt)).scalars() if "token" in m.payload]
    return str(tokens[-1] if newest else tokens[0])


async def test_a_resent_invitation_names_the_seat_it_was_sent_for_not_the_oldest(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, _, first = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "both@ashford.ac.uk", "role": "supervisor"},
    )
    second = await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "both@ashford.ac.uk", "role": "admin"},
        headers=bearer(owner),
    )
    assert second.status_code == 201, second.text
    resent = await client.post(
        f"/api/v1/orgs/ashford/memberships/{second.json()['id']}/resend-invitation", headers=bearer(owner)
    )
    assert resent.status_code in (200, 202), resent.text
    found = await client.get(f"/api/v1/auth/invitation/{await _token_for(db_session, 'both@ashford.ac.uk')}")
    assert found.json()["role"] == "admin"
    # The first email's token is spent by the resend; the stored role is on the new one only.
    assert first["role"] == "supervisor"


async def test_a_token_with_no_stored_role_falls_back_to_the_oldest_seat(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner, token, _ = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "both@ashford.ac.uk", "role": "supervisor"},
    )
    await client.post(
        "/api/v1/orgs/ashford/memberships",
        json={"email": "both@ashford.ac.uk", "role": "admin"},
        headers=bearer(owner),
    )
    # Every row of a test shares one transaction time: say which seat is the oldest.
    await db_session.execute(
        update(MembershipRow)
        .where(MembershipRow.role == "supervisor")
        .values(created_at=datetime(2026, 1, 1, tzinfo=UTC))
    )
    await db_session.execute(update(PasswordResetToken).values(membership_role=None))
    await db_session.commit()
    assert (await client.get(f"/api/v1/auth/invitation/{token}")).json()["role"] == "supervisor"


async def test_a_resend_in_one_organisation_leaves_another_organisations_invitation_live(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    owner_a, _, added_a = await _owner_and_invite(
        client,
        make_actor,
        db_session,
        path="/api/v1/orgs/ashford/memberships",
        body={"email": "shared@x.ac.uk", "role": "supervisor"},
    )
    _, org_b = await provisioned(client, make_actor, slug="bexley")
    owner_b = await make_actor(
        "owner@bexley.ac.uk",
        memberships=(Membership(org_id=org_b, org_slug="bexley", role="owner"),),
        active_org_slug="bexley",
    )
    # Same address, already an account awaiting its password: Bexley adds a seat and resends.
    added_b = await client.post(
        "/api/v1/orgs/bexley/memberships",
        json={"email": "shared@x.ac.uk", "role": "supervisor"},
        headers=bearer(owner_b),
    )
    assert added_b.status_code == 201, added_b.text
    ashford_token = await _token_for(db_session, "shared@x.ac.uk")
    resent = await client.post(
        f"/api/v1/orgs/bexley/memberships/{added_b.json()['id']}/resend-invitation", headers=bearer(owner_b)
    )
    assert resent.status_code in (200, 202), resent.text
    assert (await client.get(f"/api/v1/auth/invitation/{ashford_token}")).status_code == 200
    bexley_token = await _token_for(db_session, "shared@x.ac.uk")
    assert (await client.get(f"/api/v1/auth/invitation/{bexley_token}")).json()["organisation_name"]
    assert added_a["role"] == "supervisor"
    # Choosing a password through Bexley's link ends Ashford's too: one account, one way in.
    accepted = await client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": bexley_token, "password": "Chosen-Passw0rd!"}
    )
    assert accepted.status_code == 200, accepted.text
    assert (await client.get(f"/api/v1/auth/invitation/{ashford_token}")).status_code == 422
