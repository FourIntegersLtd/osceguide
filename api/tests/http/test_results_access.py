"""Who may touch a decision or a result, and what each route refuses with.

The workflow itself (draft, sign off, release, evidence moved) is in `test_results_routes`.
Here: every route against every kind of caller, the not-found and validation codes,
and what a candidate with no released result is told.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.support.decisions import a_sitting_and_trainee
from tests.support.roles import assert_unauthenticated, callers, refused
from tests.support.sittings import org_by_slug
from tests.support.tokens import bearer

pytestmark = pytest.mark.db

NOBODY = uuid.UUID(int=1)
BASE = "/api/v1/orgs/kings/sittings"
DRAFT = {"assessment_outcome": "pass", "rationale": "Met the standard."}

# (method, path tail under BASE/{sitting}/..., json) for every institution-admin route.
ADMIN_ROUTES = [
    ("GET", "candidates/{t}/decision", None),
    ("PUT", "candidates/{t}/decision", DRAFT),
    ("POST", "candidates/{t}/decision/sign-off", None),
    ("POST", "candidates/{t}/decision/release", None),
    ("POST", "decisions/release", {"candidates": [{"trainee_id": str(NOBODY)}]}),
    ("GET", "candidates/{t}/result.pdf", None),
]


def route_url(sitting: uuid.UUID, trainee: uuid.UUID, tail: str) -> str:
    return f"{BASE}/{sitting}/{tail.format(t=trainee)}"


async def test_only_an_institution_admin_may_decide_sign_off_release_or_print(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    for role in ("stranger", "trainee", "supervisor", "partner_admin", "platform"):
        for method, tail, body in ADMIN_ROUTES:
            await refused(client, who[role], method, route_url(NOBODY, NOBODY, tail), body)


@pytest.mark.parametrize(
    "method,tail,body,status,code",
    [
        ("PUT", "candidates/{t}/decision", DRAFT, 404, "trainee_not_found"),
        ("POST", "candidates/{t}/decision/sign-off", None, 404, "result_not_found"),
        ("POST", "candidates/{t}/decision/release", None, 404, "result_not_found"),
        ("GET", "candidates/{t}/result.pdf", None, 404, "sitting_not_found"),
    ],
)
async def test_an_admin_naming_a_candidate_or_sitting_that_does_not_exist_gets_the_literal_code(
    client: AsyncClient, make_actor, method: str, tail: str, body, status: int, code: str
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    response = await client.request(method, route_url(NOBODY, NOBODY, tail), json=body, headers=who["owner"])
    assert (response.status_code, response.json()["code"]) == (status, code), response.text


async def test_a_bulk_release_of_nobody_in_particular_skips_them_rather_than_failing(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    org_id = (await org_by_slug(db_session, "kings")).id
    sitting, trainee = await a_sitting_and_trainee(db_session, org_id)
    response = await client.post(
        f"{BASE}/{sitting}/decisions/release",
        json={"candidates": [{"trainee_id": str(trainee)}]},
        headers=who["owner"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["released"] == []
    assert [s["trainee_id"] for s in body["skipped"]] == [str(trainee)]


async def test_a_bulk_release_needs_one_to_five_hundred_candidates(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    url = f"{BASE}/{NOBODY}/decisions/release"
    empty = await client.post(url, json={"candidates": []}, headers=who["owner"])
    assert empty.status_code == 422, empty.text
    many = [{"trainee_id": str(uuid.uuid4())} for _ in range(501)]
    too_many = await client.post(url, json={"candidates": many}, headers=who["owner"])
    assert too_many.status_code == 422, too_many.text


@pytest.mark.parametrize(
    "body",
    [
        {"assessment_outcome": "excellent"},
        {"recruitment_outcome": "maybe"},
        {"expected_revision": -1},
        {"rationale": "x" * 4001},
    ],
)
async def test_a_decision_outside_the_vocabulary_is_a_validation_error(
    client: AsyncClient, make_actor, db_session: AsyncSession, body: dict
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, (await org_by_slug(db_session, "kings")).id)
    response = await client.put(
        route_url(sitting, trainee, "candidates/{t}/decision"), json=body, headers=who["owner"]
    )
    assert response.status_code == 422, response.text


async def test_signing_off_or_releasing_before_any_draft_is_a_404_and_a_draft_cannot_be_printed(
    client: AsyncClient, make_actor, db_session: AsyncSession
) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    sitting, trainee = await a_sitting_and_trainee(db_session, (await org_by_slug(db_session, "kings")).id)
    for tail in ("decision/sign-off", "decision/release"):
        response = await client.post(
            route_url(sitting, trainee, f"candidates/{{t}}/{tail}"), headers=who["owner"]
        )
        assert (response.status_code, response.json()["code"]) == (404, "result_not_found"), tail
    pdf = await client.get(route_url(sitting, trainee, "candidates/{t}/result.pdf"), headers=who["owner"])
    # Observed: with no decision at all the sitting itself is reported missing, although it exists;
    # with a draft the code is result_not_released (test_results_export). Pinned as it behaves.
    assert (pdf.status_code, pdf.json()["code"]) == (404, "sitting_not_found")


async def test_an_unknown_candidate_reads_as_no_decision_yet(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    who = await callers(client, make_actor)
    response = await client.get(route_url(NOBODY, NOBODY, "candidates/{t}/decision"), headers=who["owner"])
    assert (response.status_code, response.json()) == (200, None)


async def test_a_candidate_with_nothing_released_reads_null_and_cannot_print_or_acknowledge(
    client: AsyncClient, make_actor
) -> None:  # type: ignore[no-untyped-def]
    token = bearer(await make_actor("sat-nothing@example.com"))
    assert (await client.get(f"/api/v1/me/results/{NOBODY}", headers=token)).json() is None
    pdf = await client.get(f"/api/v1/me/results/{NOBODY}.pdf", headers=token)
    assert (pdf.status_code, pdf.json()["code"]) == (404, "result_not_released")
    ack = await client.post(f"/api/v1/me/results/{NOBODY}/acknowledge", headers=token)
    assert (ack.status_code, ack.json()["code"]) == (404, "result_not_released")


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", f"/api/v1/me/results/{NOBODY}"),
        ("GET", f"/api/v1/me/results/{NOBODY}.pdf"),
        ("POST", f"/api/v1/me/results/{NOBODY}/acknowledge"),
    ],
)
async def test_the_candidates_result_routes_need_a_token(client: AsyncClient, method: str, path: str) -> None:
    await assert_unauthenticated(client, method, path)
