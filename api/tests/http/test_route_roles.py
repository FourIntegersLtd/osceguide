"""Each route refuses the role one rung below its minimum, and a request with no credentials.

The rung is what the route's dependencies enforce (`app.core.openapi.minimum_role`,
published as `x-capability`; `tests/guards/test_route_roles.py` makes every route have
one). This calls every route as the caller one rung down and as nobody, so a stated
rung that the code does not enforce, a stream that checks too late, or a 401 or 403
the route does not declare (`tests/support/declared_codes.py`) fails here.

Ids are a nil-ish UUID: the refusal must come before any lookup, so nothing has to exist.
The exception is a role checked against the resource itself (a station's history is its owning
org's admins'): those ids are real, so the refusal is the role's and not a 404.

A second check covers `x-platform-admin`: a platform admin outside the organisation gets into
every org route that says it admits one, and is refused by every one that says it does not.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import date
from typing import Any

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient

from app.core.openapi import GRANTS, ROLE_LADDER, WORKER, admits_platform_admin, minimum_role
from app.features.growth.domain import PILOT_PARTNERS
from app.main import create_app
from tests.support.declared_codes import UndeclaredErrorCode
from tests.support.roles import callers
from tests.support.sittings import STATION_CONTENT
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

SLUG = "kings"
NOBODY = "00000000-0000-0000-0000-000000000001"
# The caller from `callers()` standing one rung below each minimum. `signed_in` has
# none: the rung below it is nobody, which every case checks.
ONE_BELOW = {
    "org_member": "stranger",
    "org_staff": "trainee",
    "org_admin": "supervisor",
    "institution_admin": "partner_admin",
    "platform_admin": "owner",
    "partner_reporter": "stranger",
}
SAMPLE: dict[Any, str] = {date: "2026-01-01", int: "1", uuid.UUID: NOBODY}
# A grant is refused with its own code; every rung with `forbidden`.
REFUSAL = {"partner_reporter": "not_a_partner_reporter"}

_ROUTES = [r for r in create_app().routes if isinstance(r, APIRoute)]


def _path(route: APIRoute, real: dict[str, str]) -> str:
    path = route.path.replace("{org_slug}", SLUG)
    for name, value in real.items():
        path = path.replace(f"{{{name}}}", value)
    path = re.sub(r"\{[^}]+\}", NOBODY, path)
    # A required query parameter is validated before a handler's own check: give it a value.
    query = [
        f"{p.alias}={SAMPLE.get(p.field_info.annotation, 'x')}"
        for p in route.dependant.query_params
        if p.field_info.is_required()
    ]
    return f"{path}?{'&'.join(query)}" if query else path


def _requests(rung: str, real: dict[str, str]) -> list[tuple[str, str]]:
    """(method, concrete path) for every route whose minimum is this rung."""
    out: list[tuple[str, str]] = []
    for route in _ROUTES:
        if minimum_role(route) == rung:
            out.extend((method, _path(route, real)) for method in sorted(route.methods))
    return out


async def _real_ids(client: AsyncClient, owner: str) -> dict[str, str]:
    """What a role checked against the resource needs to exist: a station SLUG owns, a pilot partner."""
    created = await client.post(
        f"/api/v1/orgs/{SLUG}/stations",
        json={"title": "Route roles station", "exam_code": "sca", "content": STATION_CONTENT},
        headers=bearer(owner),
    )
    assert created.status_code == 201, created.text
    return {"station_id": created.json()["id"], "partner": sorted(PILOT_PARTNERS)[0]}


async def _answer(client: AsyncClient, method: str, path: str, headers: dict[str, str]) -> Any:
    """(status, code), or why there is none. A stream that is let in never ends, so it times out."""
    try:
        response = await asyncio.wait_for(client.request(method, path, headers=headers), timeout=10)
    except TimeoutError:
        return "let in (the stream opened)"
    except UndeclaredErrorCode as exc:
        return f"undeclared: {exc}"
    try:
        body = response.json()
    except ValueError:
        body = None
    return (response.status_code, body.get("code") if isinstance(body, dict) else None)


@pytest.mark.parametrize("rung", [*ROLE_LADDER, WORKER, *GRANTS])
async def test_a_route_refuses_nobody_and_the_role_below_its_minimum(
    client: AsyncClient, make_actor: Any, rung: str
) -> None:
    who = await callers(client, make_actor, SLUG)
    requests = _requests(rung, await _real_ids(client, who.tokens["owner"]))
    assert requests, f"no route has minimum {rung!r}; drop it from the ladder or this list"
    below = ONE_BELOW.get(rung)
    refusal = (403, REFUSAL.get(rung, "forbidden"))

    wrong = []
    for method, path in requests:
        got = await _answer(client, method, path, {})
        if got != (401, "unauthenticated"):
            wrong.append(f"nobody     {method} {path}: {got}")
        if below:
            got = await _answer(client, method, path, who[below])
            if got != refusal:
                wrong.append(f"{below:<10} {method} {path}: {got}")
    assert not wrong, f"{len(wrong)} of {len(requests)} {rung} routes not refused:\n" + "\n".join(wrong)


async def test_x_platform_admin_says_whether_a_non_member_platform_admin_gets_in(
    client: AsyncClient, make_actor: Any
) -> None:
    """Every org-rung GET: admitted when the document says so, `403 forbidden` when it does not."""
    who = await callers(client, make_actor, SLUG)
    real = await _real_ids(client, who.tokens["owner"])
    org_rungs = ROLE_LADDER[1:-1]
    cases = [
        (route, admits_platform_admin(route))
        for route in _ROUTES
        if "GET" in route.methods and minimum_role(route) in org_rungs and "{org_slug}" in route.path
    ]
    assert any(admits for _, admits in cases) and not all(admits for _, admits in cases)

    wrong = []
    for route, admits in cases:
        got = await _answer(client, "GET", _path(route, real), who["platform"])
        refused = isinstance(got, tuple) and got[0] in (401, 403)
        if admits == refused:
            wrong.append(f"x-platform-admin {admits}  GET {route.path}: {got}")
    assert not wrong, f"{len(wrong)} of {len(cases)} disagree with x-platform-admin:\n" + "\n".join(wrong)
