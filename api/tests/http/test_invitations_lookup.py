"""GET /auth/invitation/{token}: the organisation that sent an invitation, and nothing else."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.identity.models import PasswordResetToken
from app.features.identity.tokens import hash_token
from app.features.notifications.models import OutboundMessage
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


async def test_a_live_invitation_names_only_its_organisation(  # type: ignore[no-untyped-def]
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    token = await _invite(client, make_actor, db_session)
    found = await client.get(f"/api/v1/auth/invitation/{token}")
    assert found.status_code == 200, found.text
    assert found.json() == {"organisation_name": "Ashford Medical School"}


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
    assert {"organisation_name": "Ashford Medical School"} in names


async def test_the_lookup_is_rate_limited(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _CountingRedis.counts = {}
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: _CountingRedis())
    statuses = [(await client.get("/api/v1/auth/invitation/guess")).status_code for _ in range(21)]
    assert statuses[:20] == [422] * 20
    assert statuses[20] == 429
