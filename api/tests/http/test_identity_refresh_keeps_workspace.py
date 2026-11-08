"""A refresh carries the workspace the person switched to, validated against their memberships."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Membership
from app.core.settings import get_settings
from app.features.identity import repository as identity_repo
from app.features.identity.tokens import new_token
from tests.http.test_tenancy_routes import seed_org


def _active_org(access_token: str) -> str | None:
    return jwt.decode(access_token, options={"verify_signature": False})["active_org"]


async def _two_org_user(client: AsyncClient, make_actor, db_session: AsyncSession):  # type: ignore[no-untyped-def]
    kings = await seed_org(client, make_actor, "kings")
    guys = await seed_org(client, make_actor, "guys")
    token = await make_actor(
        "switcher@example.com",
        memberships=(
            Membership(org_id=kings, org_slug="kings", role="trainee"),
            Membership(org_id=guys, org_slug="guys", role="trainee"),
        ),
        active_org_slug="kings",
    )
    user_id = jwt.decode(token, options={"verify_signature": False})["sub"]
    raw, hashed = new_token()
    import uuid

    await identity_repo.create_refresh_chain(
        db_session,
        user_id=uuid.UUID(user_id),
        token_hash=hashed,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await db_session.commit()
    assert get_settings()
    return raw


async def _refresh(client: AsyncClient, raw: str, **extra: object) -> dict:  # type: ignore[type-arg]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw, **extra})
    assert response.status_code == 200, response.text
    return response.json()


async def test_refresh_without_a_hint_lands_in_the_default_workspace(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    raw = await _two_org_user(client, make_actor, db_session)
    default = _active_org((await _refresh(client, raw))["access_token"])
    assert default in {"kings", "guys"}


async def test_refresh_keeps_the_org_the_person_switched_to(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    raw = await _two_org_user(client, make_actor, db_session)
    first = await _refresh(client, raw)
    other = "guys" if _active_org(first["access_token"]) == "kings" else "kings"
    body = await _refresh(client, first["refresh_token"], active_org_slug=other)
    assert _active_org(body["access_token"]) == other


async def test_refresh_keeps_the_personal_workspace(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    raw = await _two_org_user(client, make_actor, db_session)
    body = await _refresh(client, raw, active_org_slug=None)
    assert _active_org(body["access_token"]) is None


async def test_refresh_never_lands_in_an_org_the_person_is_not_in(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:
    raw = await _two_org_user(client, make_actor, db_session)
    await seed_org(client, make_actor, "strangers")
    body = await _refresh(client, raw, active_org_slug="strangers")
    assert _active_org(body["access_token"]) in {"kings", "guys"}
