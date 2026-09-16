"""Fail a test the moment a route answers with an error code it never declared.

`error_responses(...)` puts each route's error vocabulary in the OpenAPI
document as `x-codes`, and the frontend is meant to switch on those values.
Nothing checked that the list was true: a service could raise `SlotLocked`
from a route that documents only `circuit_not_found`, and the client would
meet a 409 code its generated types have never heard of.

Static analysis of what a service can raise is not sound across the
service -> domain -> repository call chain. Observing what the app actually
returns is, so the check runs against real responses in the real suite and
gets stronger as coverage does.

Checked at the moment it happens rather than collected for a session-end
report, so the failure names the test that caused it.
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# FastAPI raises this itself for a malformed body, on every route, without the
# route declaring it. It is in the document as `HTTPValidationError`.
AMBIENT = {(422, "invalid_input")}


class UndeclaredErrorCode(AssertionError):
    pass


def _declared(route: object, status: int) -> set[str] | None:
    responses = getattr(route, "responses", None) or {}
    entry = responses.get(status) or responses.get(str(status))
    if entry is None:
        return None
    return set(entry.get("x-codes") or [])


class AssertDeclaredErrorCodes(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        if response.status_code < 400:
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        rebuilt = Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        try:
            code = json.loads(body).get("code")
        except (ValueError, AttributeError):
            return rebuilt
        if code is None or (response.status_code, code) in AMBIENT:
            return rebuilt

        route = request.scope.get("route")
        if route is None:  # 404 for a path that matches nothing
            return rebuilt

        declared = _declared(route, response.status_code)
        if declared is None or code not in declared:
            raise UndeclaredErrorCode(
                f"{request.method} {getattr(route, 'path', request.url.path)} answered "
                f"{response.status_code} {code!r}, which it does not declare. Add the "
                f"error class to this route's `error_responses(...)` so the frontend's "
                f"generated types know the code. Declared for {response.status_code}: "
                f"{sorted(declared) if declared is not None else 'nothing'}."
            )
        return rebuilt


def install(app: FastAPI) -> None:
    app.add_middleware(AssertDeclaredErrorCodes)
