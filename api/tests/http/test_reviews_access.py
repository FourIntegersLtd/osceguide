"""Who may review, and what each review route refuses with.

The review behaviour (drafts, ratings, locking, merging) is in `test_reviews_routes`.
Here: every route against every kind of caller, the not-found codes, and the bodies
a route must refuse before it reaches the service.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.support.roles import assert_unauthenticated, callers, refused
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOBODY = uuid.UUID(int=1)
ORG = "/api/v1/orgs/kings"
SLOT = f"{ORG}/slots/{NOBODY}"
CIRCUIT = f"{ORG}/circuits/{NOBODY}"

STAFF_ROUTES = [
    ("GET", f"{SLOT}/reviews", None),
    ("POST", f"{SLOT}/marking/retry", None),
    ("GET", f"{SLOT}/reviews/mine", None),
    ("PUT", f"{SLOT}/reviews/mine", {"field_values": {}, "status": "draft"}),
    ("DELETE", f"{SLOT}/reviews/{NOBODY}", None),
    ("POST", f"{CIRCUIT}/review/finalize", {"merged_notes": "ok"}),
    ("GET", f"{CIRCUIT}/review", None),
]
ADMIN_ROUTES = [
    ("GET", f"{SLOT}/gp-lead-review", None),
    ("PUT", f"{SLOT}/gp-lead-review", {"revision": 0, "field_values": {}, "status": "draft"}),
    ("DELETE", f"{SLOT}/gp-lead-review", None),
]


async def test_review_routes_refuse_every_caller_who_may_not_use_them(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for role in ("stranger", "trainee"):
        for method, path, body in STAFF_ROUTES + ADMIN_ROUTES:
            await refused(client, who[role], method, path, body)
    # the GP lead review is for institution admins alone
    for role in ("supervisor", "partner_admin", "platform"):
        for method, path, body in ADMIN_ROUTES:
            await refused(client, who[role], method, path, body)


@pytest.mark.parametrize("role", ["supervisor", "owner"])
@pytest.mark.parametrize(
    "method,path,body,status,code",
    [
        ("GET", f"{SLOT}/reviews", None, 200, None),
        ("POST", f"{SLOT}/marking/retry", None, 404, "slot_not_found"),
        ("GET", f"{SLOT}/reviews/mine", None, 404, "slot_not_found"),
        ("PUT", f"{SLOT}/reviews/mine", {"field_values": {}, "status": "draft"}, 404, "slot_not_found"),
        ("DELETE", f"{SLOT}/reviews/{NOBODY}", None, 404, "slot_not_found"),
        ("POST", f"{CIRCUIT}/review/finalize", {"merged_notes": "ok"}, 404, "circuit_not_found"),
        ("GET", f"{CIRCUIT}/review", None, 200, None),
    ],
)
async def test_staff_naming_something_that_does_not_exist_get_the_literal_answer(
    client: AsyncClient, make_actor, role: str, method: str, path: str, body, status: int, code: str | None
) -> None:  # type: ignore[no-untyped-def]
    headers = (await callers(client, make_actor))[role]
    response = await client.request(method, path, json=body, headers=headers)
    assert response.status_code == status, response.text
    if code:
        assert response.json()["code"] == code


@pytest.mark.parametrize(
    "method,path,body,status,code",
    [
        ("GET", f"{SLOT}/gp-lead-review", None, 200, None),
        (
            "PUT",
            f"{SLOT}/gp-lead-review",
            {"revision": 0, "field_values": {}, "status": "draft"},
            404,
            "slot_not_found",
        ),
        ("DELETE", f"{SLOT}/gp-lead-review", None, 404, "slot_not_found"),
    ],
)
async def test_an_institution_admin_naming_a_missing_slot_gets_the_literal_answer(
    client: AsyncClient, make_actor, method: str, path: str, body, status: int, code: str | None
) -> None:  # type: ignore[no-untyped-def]
    headers = (await callers(client, make_actor))["owner"]
    response = await client.request(method, path, json=body, headers=headers)
    assert response.status_code == status, response.text
    if code:
        assert response.json()["code"] == code


async def test_a_circuit_and_a_slot_with_no_review_yet_read_as_null(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    owner = (await callers(client, make_actor))["owner"]
    assert (await client.get(f"{CIRCUIT}/review", headers=owner)).json() is None
    assert (await client.get(f"{SLOT}/gp-lead-review", headers=owner)).json() is None


async def test_my_slot_review_needs_a_token_and_a_slot_that_is_mine(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/me/slots/{NOBODY}/review"
    await assert_unauthenticated(client, "GET", path)
    someone = bearer(await make_actor("reviewed@example.com"))
    missing = await client.get(path, headers=someone)
    assert (missing.status_code, missing.json()["code"]) == (404, "slot_not_found")
