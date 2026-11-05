"""The body limit answers 413 before the handler runs, with or without a declared size."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from fastapi import FastAPI, Request

from app.core.body_limit import BodyLimitMiddleware

LIMIT = 1000


def build() -> tuple[FastAPI, list[str]]:
    ran: list[str] = []
    app = FastAPI()

    @app.post("/upload")
    async def upload(request: Request) -> dict[str, int]:
        ran.append("handler")
        return {"bytes": len(await request.body())}

    app.add_middleware(BodyLimitMiddleware, max_bytes=LIMIT)
    return app, ran


async def post(app: FastAPI, path: str, content: bytes | AsyncIterator[bytes]) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
        return await client.post(path, content=content)


async def test_declared_size_over_the_limit_is_refused_without_running_the_handler() -> None:
    app, ran = build()
    response = await post(app, "/upload", b"x" * (LIMIT + 1))
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"
    assert ran == []


async def test_body_at_the_limit_goes_through() -> None:
    app, _ = build()
    response = await post(app, "/upload", b"x" * LIMIT)
    assert response.status_code == 200
    assert response.json() == {"bytes": LIMIT}


async def test_a_stream_with_no_declared_size_is_cut_off_when_it_passes_the_limit() -> None:
    app, _ = build()

    async def pieces() -> AsyncIterator[bytes]:
        for _ in range(5):
            yield b"x" * 300

    response = await post(app, "/upload", pieces())
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


async def test_a_chunked_stream_to_a_route_with_a_declared_body_is_413_not_400() -> None:
    app, _ = build()

    @app.post("/json")
    async def declared(payload: dict[str, str]) -> dict[str, str]:
        return payload

    async def pieces() -> AsyncIterator[bytes]:
        yield b'{"a": "' + b"x" * (LIMIT + 10) + b'"}'

    response = await post(app, "/json", pieces())
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


async def test_a_30_mib_upload_to_the_real_app_is_refused_before_auth_or_handler() -> None:
    from app.main import app

    response = await post(app, "/api/v1/cv", b"x" * (30 * 1024 * 1024))
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"
