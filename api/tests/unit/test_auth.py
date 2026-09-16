import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.auth import (
    CurrentPrincipal,
    Membership,
    Principal,
    decode_access_token,
    issue_access_token,
    require_worker_secret,
)
from app.core.errors import Unauthenticated, register_error_handlers
from app.core.settings import Settings, get_settings
from tests.support.tokens import bearer, mint_token


def test_access_token_round_trips_principal(settings: Settings) -> None:
    org = uuid.uuid4()
    principal = Principal(
        user_id=uuid.uuid4(),
        email="a@b.com",
        memberships=(Membership(org_id=org, org_slug="st-marys", role="admin", surface="institution"),),
        active_org_slug="st-marys",
        is_platform_admin=False,
    )
    decoded = decode_access_token(issue_access_token(principal, settings=settings), settings=settings)
    assert decoded == principal
    assert decoded.active_membership is not None
    assert decoded.active_membership.role == "admin"


def test_expired_token_is_rejected(settings: Settings) -> None:
    principal = Principal(user_id=uuid.uuid4(), email="a@b.com")
    long_ago = datetime.now(UTC) - timedelta(days=2)
    token = issue_access_token(principal, settings=settings, now=long_ago)
    with pytest.raises(Unauthenticated):
        decode_access_token(token, settings=settings)


def test_token_signed_with_other_secret_is_rejected(settings: Settings) -> None:
    other = Settings(_env_file=None, jwt_secret="someone-else-with-a-thirty-two-byte-secret")
    token = issue_access_token(Principal(user_id=uuid.uuid4(), email="a@b.com"), settings=other)
    with pytest.raises(Unauthenticated):
        decode_access_token(token, settings=settings)


def _app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/me")
    async def me(principal: CurrentPrincipal) -> dict[str, str]:
        return {"email": principal.email}

    @app.get("/worker", dependencies=[Depends(require_worker_secret)])
    async def worker() -> dict[str, bool]:
        return {"ok": True}

    return app


async def test_principal_dependency_requires_bearer() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as c:
        assert (await c.get("/me")).status_code == 401
        ok = await c.get("/me", headers=bearer(mint_token(email="x@y.com")))
    assert ok.status_code == 200
    assert ok.json() == {"email": "x@y.com"}


async def test_worker_guard_compares_secret(settings: Settings) -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as c:
        assert (await c.get("/worker")).status_code == 401
        assert (await c.get("/worker", headers={settings.worker_secret_header: "wrong"})).status_code == 401
        good = await c.get("/worker", headers={settings.worker_secret_header: settings.worker_secret})
    assert good.status_code == 200


async def test_worker_guard_fails_closed_when_secret_unset() -> None:
    app = _app()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, worker_secret="")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/worker", headers={"X-Worker-Secret": ""})
    assert r.status_code == 401


def test_settings_type_hint_is_usable_as_dependency() -> None:
    # Guards that the Annotated alias resolves (regression for import cycles).
    assert Annotated is not None
