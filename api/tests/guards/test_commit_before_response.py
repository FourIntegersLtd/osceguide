"""A write is committed before its answer leaves the server.

A client that is told 201 acts on it at once: the e2e setup registers an account and seats
it in an organisation in the next request. FastAPI runs the exit of a `yield` dependency
with the default ("request") scope only after the response has been sent, so the request
session's commit raced the client's next request: the seat read no account, inserted one,
blocked on the register's uncommitted row and failed `uq_users_email` with a 500 (CI web
journeys, 0423c0b0). It also means a 2xx could be sent for a write whose commit then fails.

The in-process `client` cannot see this: `ASGITransport` waits for the whole app, and the
test override of `get_session` shares one transaction. So the first test drives the real
`get_session` and records whether the commit or the last byte of the answer came first; the
second keeps every route on the scope that commits first.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as OrmSession
from starlette.types import Message, Receive, Scope, Send

from app.core.db import get_session, get_session_factory
from app.features.identity.models import User


def _session_dependants(dependant: Dependant) -> Iterator[Dependant]:
    for sub in dependant.dependencies:
        if sub.call is get_session:
            yield sub
        yield from _session_dependants(sub)


@pytest.mark.db
async def test_the_account_is_committed_before_register_answers(db_session: AsyncSession) -> None:
    from app.main import create_app

    app = create_app()  # no test overrides: the real request session
    email = f"commit-{uuid.uuid4().hex[:10]}@example.com"
    happened: list[str] = []

    def committed(_session: OrmSession) -> None:
        happened.append("commit")

    async def watching(scope: Scope, receive: Receive, send: Send) -> None:
        async def spy(message: Message) -> None:
            if message["type"] == "http.response.body" and not message.get("more_body"):
                happened.append("answered")
            await send(message)

        await app(scope, receive, spy)

    event.listen(OrmSession, "after_commit", committed)
    try:
        async with AsyncClient(transport=ASGITransport(app=watching), base_url="http://test") as http:
            answer = await http.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "Correct-horse-9-battery", "name": "Commit Check"},
            )
        assert answer.status_code == 201, answer.text
        assert "commit" in happened
        assert happened.index("commit") < happened.index("answered"), happened
    finally:
        event.remove(OrmSession, "after_commit", committed)
        async with get_session_factory()() as cleanup, cleanup.begin():
            await cleanup.execute(delete(User).where(User.email == email))


def test_every_route_commits_before_it_answers(built_app) -> None:  # type: ignore[no-untyped-def]
    late = sorted(
        f"{','.join(sorted(route.methods))} {route.path}"
        for route in built_app.routes
        if isinstance(route, APIRoute)
        for sub in _session_dependants(route.dependant)
        if sub.scope != "function"
    )
    assert late == [], (
        'Depends(get_session) without scope="function" commits after the answer is sent: ' + ", ".join(late)
    )


def test_only_session_dep_reaches_the_request_session() -> None:
    api_root = Path(__file__).resolve().parents[2]
    core_db = api_root / "app" / "core" / "db.py"
    offenders = sorted(
        str(path.relative_to(api_root))
        for path in (api_root / "app").rglob("*.py")
        if path != core_db and "Depends(get_session" in path.read_text(encoding="utf-8")
    )
    assert offenders == [], "use SessionDep instead of Depends(get_session): " + ", ".join(offenders)
