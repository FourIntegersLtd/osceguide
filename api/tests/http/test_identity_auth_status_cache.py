"""The auth-status cache: an "active" answer is kept for seconds, and nothing else ever is.

Item 8 of the exam-day plan. The risk is a deactivated person or a suspended organisation staying in
for the length of the cache, so each write that changes a status is proven to bite on the very next
request, against a real Redis (`seat_redis`), and the same flows are proven with Redis erroring.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cache
from app.core.account_status import status_key
from app.core.db import get_session
from app.core.tenancy import org_active_key
from tests.http.test_identity_routes import REGISTER, register
from tests.http.test_tenancy_routes import member_token, seed_org
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


@pytest.fixture(autouse=True)
def _flush_cache_ops_after_each_request(app, db_session: AsyncSession) -> None:  # type: ignore[no-untyped-def]
    """The shared test session override only flushes events; production also runs the queued cache
    operations after the commit (`core.db.flush_after_commit`). Wrap it so this module sees that."""
    inner = app.dependency_overrides[get_session]

    async def with_cache_flush() -> AsyncIterator[AsyncSession]:
        generator = inner()
        session = await generator.__anext__()
        try:
            yield session
        except BaseException as exc:
            await generator.athrow(exc)
            raise
        await generator.aclose()
        await cache.flush_cache_ops(session)

    app.dependency_overrides[get_session] = with_cache_flush


@pytest_asyncio.fixture
async def redis(seat_redis, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cache, "get_redis", lambda: seat_redis)
    keys: list[str] = []
    yield seat_redis, keys
    for key in keys:
        await seat_redis.delete(f"cache:{key}")


class _BrokenRedis:
    """Every call errors, as Redis does mid-outage."""

    async def get(self, *_a: object, **_k: object) -> None:
        raise ConnectionError("redis is down")

    set = delete = incr = get


async def test_a_deactivated_account_is_refused_on_the_next_request(
    client: AsyncClient, make_actor, redis
) -> None:  # type: ignore[no-untyped-def]
    client_redis, keys = redis
    root = await make_actor("root@osceguide.com", platform_admin=True)
    registered = (await register(client, email="leaver@example.com")).json()
    access, user_id = registered["access_token"], registered["user"]["id"]
    keys.append(status_key(uuid.UUID(user_id)))

    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 200
    assert await client_redis.get(f"cache:{status_key(uuid.UUID(user_id))}") == "active"
    ttl = await client_redis.ttl(f"cache:{status_key(uuid.UUID(user_id))}")
    assert 0 < ttl <= 30
    assert (
        await client.get("/api/v1/me", headers=bearer(access))
    ).status_code == 200  # served from the cache

    gone = await client.patch(
        f"/api/v1/platform/users/{user_id}", json={"status": "deactivated"}, headers=bearer(root)
    )
    assert gone.status_code == 200, gone.text
    assert await client_redis.get(f"cache:{status_key(uuid.UUID(user_id))}") is None

    refused = await client.get("/api/v1/me", headers=bearer(access))
    assert (refused.status_code, refused.json()["code"]) == (401, "account_suspended")
    assert await client_redis.get(f"cache:{status_key(uuid.UUID(user_id))}") is None, (
        "a refusal is never cached"
    )


async def test_closing_an_account_drops_its_cached_status(client: AsyncClient, redis) -> None:  # type: ignore[no-untyped-def]
    client_redis, keys = redis
    registered = (await register(client, email="closer@example.com")).json()
    access, user_id = registered["access_token"], uuid.UUID(registered["user"]["id"])
    keys.append(status_key(user_id))
    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 200
    assert await client_redis.get(f"cache:{status_key(user_id)}") == "active"

    closed = await client.post(
        "/api/v1/me/close", json={"password": REGISTER["password"]}, headers=bearer(access)
    )
    assert closed.status_code in (200, 204), closed.text

    assert await client_redis.get(f"cache:{status_key(user_id)}") is None
    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 401


async def test_a_platform_admin_is_never_served_from_the_cache(
    client: AsyncClient, make_actor, redis
) -> None:  # type: ignore[no-untyped-def]
    client_redis, keys = redis
    root = await make_actor("staff@osceguide.com", platform_admin=True)
    assert (await client.get("/api/v1/platform/organizations", headers=bearer(root))).status_code == 200
    # The admin's own key is the one that matters: none was written for them.
    from app.core.auth import decode_access_token
    from app.core.settings import get_settings

    admin_id = decode_access_token(root, settings=get_settings()).user_id
    assert await client_redis.get(f"cache:{status_key(admin_id)}") is None


async def test_a_suspended_organisation_is_refused_on_the_next_request(
    client: AsyncClient, make_actor, redis
) -> None:  # type: ignore[no-untyped-def]
    client_redis, keys = redis
    keys.append(org_active_key("kings"))
    org_id = await seed_org(client, make_actor)
    owner = await member_token(make_actor, org_id, "kings", "owner")
    root = await make_actor("root2@osceguide.com", platform_admin=True)

    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(owner))).status_code == 200
    assert await client_redis.get(f"cache:{org_active_key('kings')}") == "active"
    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(owner))).status_code == 200

    assert (
        await client.post("/api/v1/platform/organizations/kings/suspend", headers=bearer(root))
    ).status_code == 200
    assert await client_redis.get(f"cache:{org_active_key('kings')}") is None

    blocked = await client.get("/api/v1/orgs/kings/trainees", headers=bearer(owner))
    assert (blocked.status_code, blocked.json()["code"]) == (403, "organization_suspended")
    assert await client_redis.get(f"cache:{org_active_key('kings')}") is None, "a refusal is never cached"


async def test_a_lapsed_contract_edit_drops_the_cached_organisation(
    client: AsyncClient, make_actor, redis
) -> None:  # type: ignore[no-untyped-def]
    client_redis, keys = redis
    keys.append(org_active_key("kings"))
    org_id = await seed_org(client, make_actor)
    owner = await member_token(make_actor, org_id, "kings", "owner")
    root = await make_actor("root3@osceguide.com", platform_admin=True)
    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(owner))).status_code == 200

    edited = await client.patch(
        "/api/v1/platform/organizations/kings", json={"name": "Kings again"}, headers=bearer(root)
    )
    assert edited.status_code == 200, edited.text
    assert await client_redis.get(f"cache:{org_active_key('kings')}") is None


async def test_with_redis_erroring_a_deactivated_account_is_still_refused(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cache, "get_redis", lambda: _BrokenRedis())
    root = await make_actor("root4@osceguide.com", platform_admin=True)
    registered = (await register(client, email="outage@example.com")).json()
    access, user_id = registered["access_token"], registered["user"]["id"]
    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 200

    await client.patch(
        f"/api/v1/platform/users/{user_id}", json={"status": "deactivated"}, headers=bearer(root)
    )

    refused = await client.get("/api/v1/me", headers=bearer(access))
    assert (refused.status_code, refused.json()["code"]) == (401, "account_suspended")


async def test_with_redis_erroring_a_suspended_organisation_is_still_refused(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cache, "get_redis", lambda: _BrokenRedis())
    root = await make_actor("root6@osceguide.com", platform_admin=True)
    org_id = await seed_org(client, make_actor)
    owner = await member_token(make_actor, org_id, "kings", "owner")
    assert (await client.get("/api/v1/orgs/kings/trainees", headers=bearer(owner))).status_code == 200
    await client.post("/api/v1/platform/organizations/kings/suspend", headers=bearer(root))
    blocked = await client.get("/api/v1/orgs/kings/trainees", headers=bearer(owner))
    assert (blocked.status_code, blocked.json()["code"]) == (403, "organization_suspended")


async def test_with_redis_off_the_same_requests_give_the_same_answers(
    client: AsyncClient, make_actor, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cache, "get_redis", lambda: None)
    root = await make_actor("root5@osceguide.com", platform_admin=True)
    registered = (await register(client, email="off@example.com")).json()
    access, user_id = registered["access_token"], registered["user"]["id"]
    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 200
    await client.patch(
        f"/api/v1/platform/users/{user_id}", json={"status": "deactivated"}, headers=bearer(root)
    )
    assert (await client.get("/api/v1/me", headers=bearer(access))).status_code == 401
