from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import Conflict, NotFound, error_responses, register_error_handlers
from app.core.logging import RequestContextMiddleware


class SlotLocked(Conflict):
    code = "slot_locked"
    default_message = "Slot is locked"


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    @app.get("/missing")
    async def missing() -> None:
        raise NotFound("No such thing", details={"id": "42"})

    @app.get("/locked")
    async def locked() -> None:
        raise SlotLocked()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    @app.get("/typed")
    async def typed(n: int) -> dict[str, int]:
        return {"n": n}

    return app


async def test_app_error_maps_type_to_status_and_code() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/missing")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "not_found"
    assert body["message"] == "No such thing"
    assert body["details"] == {"id": "42"}
    assert body["request_id"] == r.headers["X-Request-ID"]


async def test_subclass_carries_its_own_code() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/locked")
    assert r.status_code == 409
    assert r.json()["code"] == "slot_locked"


async def test_unhandled_exception_never_leaks_detail() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_app(), raise_app_exceptions=False), base_url="http://t"
    ) as c:
        r = await c.get("/boom")
    assert r.status_code == 500
    assert "secret" not in r.text
    assert r.json()["code"] == "internal_error"


async def test_validation_errors_share_the_error_shape() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/typed", params={"n": "not-a-number"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "invalid_input"
    assert body["details"]["errors"][0]["loc"] == ["query", "n"]


def test_error_responses_groups_codes_by_status() -> None:
    spec = error_responses(NotFound, Conflict, SlotLocked)
    assert set(spec) == {404, 409}
    assert spec[409]["description"] == "conflict, slot_locked"
