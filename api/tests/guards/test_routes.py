"""Every mounted route keeps the contract promises.

Checked at runtime over the real app, so nothing depends on how a router file
is written:
- worker routes are guarded by the worker secret;
- every route declares a response model (the OpenAPI document is the
  frontend's contract, and an undeclared response is an empty promise);
- every public route documents its error responses.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI, status
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.core.auth import require_worker_secret
from app.core.openapi import SSE_MEDIA_TYPE
from app.main import API_V1_PREFIX, WORKER_PREFIX, create_app

INFRA_PATHS = {"/health"}


def _dependency_callables(dep: Dependant) -> Iterator[object]:
    for sub in dep.dependencies:
        yield sub.call
        yield from _dependency_callables(sub)


def api_routes(app: FastAPI) -> list[APIRoute]:
    return [r for r in app.routes if isinstance(r, APIRoute)]


@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


def test_there_are_routes_to_check(app: FastAPI) -> None:
    assert api_routes(app), "no routes mounted; the guard would pass vacuously"


def test_every_worker_route_requires_the_worker_secret(app: FastAPI) -> None:
    unguarded = [
        r.path
        for r in api_routes(app)
        if r.path.startswith(WORKER_PREFIX)
        and require_worker_secret not in set(_dependency_callables(r.dependant))
    ]
    assert not unguarded, f"worker routes without require_worker_secret: {unguarded}"


def streams_events(route: APIRoute) -> bool:
    """Whether this route's 200 is declared as a server-sent event stream."""
    declared = route.responses.get(200, {})
    return SSE_MEDIA_TYPE in declared.get("content", {})


def test_every_route_declares_a_response_model(app: FastAPI) -> None:
    """A route returns a declared shape, so the generated client has a type.

    204 is exempt: it means "no content", and declaring a body model for one
    would put a lie in the OpenAPI document.

    A `text/event-stream` route is exempt from `response_model` for the same
    reason and no further: its body is an unbounded sequence of frames, not one
    object. It is not exempt from declaring a shape — the test below requires
    it to name the schema each frame carries.
    """
    missing = [
        f"{sorted(r.methods)} {r.path}"
        for r in api_routes(app)
        if r.response_model is None and r.status_code != status.HTTP_204_NO_CONTENT and not streams_events(r)
    ]
    assert not missing, f"routes without response_model: {missing}"


def test_every_stream_names_the_schema_its_frames_carry(app: FastAPI) -> None:
    """A stream that documents no frame shape is an untyped client method.

    The exemption above is what makes this necessary: without it a streaming
    route could declare nothing at all and the generated TypeScript would hand
    the caller a string to parse by hand — which is how b2c's six SSE endpoints
    came to have six hand-written, drifting payload interfaces.
    """
    undeclared = [
        f"{sorted(r.methods)} {r.path}"
        for r in api_routes(app)
        if streams_events(r) and "$ref" not in r.responses[200]["content"][SSE_MEDIA_TYPE].get("schema", {})
    ]
    assert not undeclared, f"SSE routes with no frame schema (use sse_responses): {undeclared}"


def test_the_guard_would_catch_an_undeclared_stream() -> None:
    """The planted violation: a stream that says nothing about its frames."""
    from fastapi import APIRouter

    probe = FastAPI()
    router = APIRouter()

    @router.get("/bare", responses={200: {"content": {SSE_MEDIA_TYPE: {}}}})
    async def bare() -> None:  # pragma: no cover - never called
        return None

    probe.include_router(router)
    route = next(r for r in api_routes(probe) if r.path == "/bare")
    assert streams_events(route)
    assert "$ref" not in route.responses[200]["content"][SSE_MEDIA_TYPE].get("schema", {})


def test_every_public_route_documents_its_errors(app: FastAPI) -> None:
    public = [r for r in api_routes(app) if r.path.startswith((API_V1_PREFIX, WORKER_PREFIX))]
    undocumented = [f"{sorted(r.methods)} {r.path}" for r in public if not r.responses]
    assert not undocumented, f"routes without error responses (use error_responses(...)): {undocumented}"


def test_the_guard_sees_dependencies_through_nesting() -> None:
    """A planted unguarded worker route is reported."""
    from fastapi import APIRouter, Depends

    probe = FastAPI()
    router = APIRouter()

    @router.get(f"{WORKER_PREFIX}/open", response_model=dict)
    async def open_route() -> dict:  # pragma: no cover - never called
        return {}

    @router.get(f"{WORKER_PREFIX}/closed", response_model=dict, dependencies=[Depends(require_worker_secret)])
    async def closed_route() -> dict:  # pragma: no cover - never called
        return {}

    probe.include_router(router)
    guarded = {
        r.path for r in api_routes(probe) if require_worker_secret in set(_dependency_callables(r.dependant))
    }
    assert guarded == {f"{WORKER_PREFIX}/closed"}


def test_operation_ids_are_unique(app: FastAPI) -> None:
    """The generated client names a method per operation id.

    Two routes sharing one silently loses a method, which surfaces as a missing
    function in the frontend rather than as anything resembling an error here.
    Both worker routers had `bootstrap` and `accept_transcript` before this
    existed.
    """
    import collections

    # From the generated document, not from `route.operation_id`: FastAPI fills
    # that in while building the schema, so reading it off the route compares
    # bare function names and misses the thing being tested.
    document = app.openapi()
    ids = [
        operation["operationId"]
        for path in document["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    duplicates = [oid for oid, count in collections.Counter(ids).items() if count > 1]
    assert not duplicates, f"duplicate operation ids: {duplicates}"


def test_every_tag_used_by_a_route_is_described(app: FastAPI) -> None:
    """A tag with no description is an undocumented section in the client."""
    from app.core.openapi import TAGS

    described = {tag["name"] for tag in TAGS}
    used = {tag for route in api_routes(app) for tag in (route.tags or [])}
    assert used <= described, f"tags used but not described: {sorted(used - described)}"
