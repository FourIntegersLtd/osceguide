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
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.core.auth import require_worker_secret
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


def test_every_route_declares_a_response_model(app: FastAPI) -> None:
    missing = [f"{sorted(r.methods)} {r.path}" for r in api_routes(app) if r.response_model is None]
    assert not missing, f"routes without response_model: {missing}"


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
