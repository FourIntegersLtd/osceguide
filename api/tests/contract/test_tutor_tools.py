"""What a dashboard session offers the worker, and what its tools answer.

Payload shapes from `livekit_assistant_worker/bootstrap.py` (`session.tools[]`)
and `tools/remote.py` (`{tool, arguments, call_id}` in, `{result, display}`
out). The tool path is hardcoded in the worker, so it is spelled here exactly.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.features.tutor_memory import repository, tools_catalog
from tests.support.fakes import FakeTutorPromptRenderer
from tests.support.tokens import bearer

pytestmark = pytest.mark.db


def worker_headers() -> dict[str, str]:
    settings = get_settings()
    return {settings.worker_secret_header: settings.worker_secret}


@pytest.fixture
def tutor_renderer(monkeypatch: pytest.MonkeyPatch) -> FakeTutorPromptRenderer:
    """Stand in for the engine, which is an optional dependency here.

    What the prompt says is the engine's and has a golden of its own, checked
    by `test_tutor_prompt_oracle.py`. What this side owns is that a brief was
    composed and handed over, so the fake records it and returns a marker.

    Wrapped rather than patched: the fake goes in through the service's own
    optional `renderer` argument, which exists for exactly this.
    """
    from app.features.tutor_memory import service_session

    fake = FakeTutorPromptRenderer()
    original = service_session.render_dashboard_session

    async def with_fake(session, **kwargs):  # type: ignore[no-untyped-def]
        return await original(session, renderer=fake, **kwargs)

    monkeypatch.setattr(service_session, "render_dashboard_session", with_fake)
    return fake


async def a_dashboard_session(client: AsyncClient, token: str) -> str:
    created = await client.post(
        "/api/v1/assistant/sessions", json={"session_type": "dashboard"}, headers=bearer(token)
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


async def test_a_dashboard_bootstrap_carries_the_four_tools(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tools-bootstrap@example.com")
    session_id = await a_dashboard_session(client, token)

    payload = (
        await client.get(f"/api/worker/assistant-sessions/{session_id}", headers=worker_headers())
    ).json()["session"]

    assert [t["name"] for t in payload["tools"]] == [t["name"] for t in tools_catalog.CATALOG]
    assert all(t["parameters"]["type"] == "object" for t in payload["tools"])
    assert FakeTutorPromptRenderer.MARKER in payload["instructions"]


async def test_a_help_bootstrap_still_carries_no_tools(client: AsyncClient, make_actor) -> None:  # type: ignore[no-untyped-def]
    """An empty list is the whole of the old behaviour."""
    token = await make_actor("tools-help@example.com")
    created = await client.post(
        "/api/v1/assistant/sessions", json={"session_type": "help"}, headers=bearer(token)
    )
    session_id = created.json()["id"]

    payload = (
        await client.get(f"/api/worker/assistant-sessions/{session_id}", headers=worker_headers())
    ).json()["session"]

    assert payload["tools"] == []


async def test_a_first_conversation_is_greeted_differently_from_a_returning_one(
    client: AsyncClient, db_session: AsyncSession, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo
    from app.features.tutor_memory import service_session

    email = "tools-greeting@example.com"
    token = await make_actor(email)
    first = await a_dashboard_session(client, token)
    greeting_url = f"/api/worker/assistant-sessions/{first}"
    assert (await client.get(greeting_url, headers=worker_headers())).json()["session"][
        "greeting"
    ] == service_session.GREETING_FIRST_TIME

    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    await repository.add_note(
        db_session,
        user_id=user.id,
        exam_id=None,
        session_id=None,
        kind="session_summary",
        body={"summary": "We went over the hip consultation.", "agreed_next_steps": []},
    )

    second = await a_dashboard_session(client, token)
    payload = (await client.get(f"/api/worker/assistant-sessions/{second}", headers=worker_headers())).json()[
        "session"
    ]
    assert payload["greeting"] == service_session.GREETING_RETURNING


async def test_remember_writes_a_fact_the_next_brief_carries(
    client: AsyncClient, db_session: AsyncSession, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    from app.features.identity import repository as identity_repo

    email = "tools-remember@example.com"
    token = await make_actor(email)
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/remember",
        json={"tool": "remember", "arguments": {"fact": "Their exam is in six weeks"}, "call_id": "c1"},
        headers=worker_headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["display"] is None
    user = await identity_repo.user_by_email(db_session, email)
    assert user is not None
    notes = await repository.notes_of_kind(db_session, user.id, kind="stated_fact", limit=5)
    assert [n.body["fact"] for n in notes] == ["Their exam is in six weeks"]


async def test_recall_answers_from_what_was_remembered(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tools-recall@example.com")
    session_id = await a_dashboard_session(client, token)
    url = f"/api/worker/assistant-sessions/{session_id}/tools"
    await client.post(
        f"{url}/remember",
        json={"tool": "remember", "arguments": {"fact": "They find follow-up timing hardest"}},
        headers=worker_headers(),
    )

    response = await client.post(
        f"{url}/recall_history",
        json={"tool": "recall_history", "arguments": {"query": "follow-up", "kind": "note"}},
        headers=worker_headers(),
    )

    assert "follow-up timing" in response.json()["result"]


async def test_recall_with_nothing_on_file_says_so_rather_than_guessing(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    from app.features.tutor_memory import service_tools

    token = await make_actor("tools-empty@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/recall_history",
        json={"tool": "recall_history", "arguments": {"query": "anything at all"}},
        headers=worker_headers(),
    )

    assert response.json()["result"] == service_tools.NOTHING_FOUND


async def test_searching_material_says_it_is_not_configured(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    """Until the material index lands, the tutor says so plainly."""
    from app.features.tutor_memory import service_tools

    token = await make_actor("tools-search@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/search_material",
        json={"tool": "search_material", "arguments": {"query": "asthma management"}},
        headers=worker_headers(),
    )

    assert response.json()["result"] == service_tools.NOT_CONFIGURED


async def test_suggesting_something_they_cannot_open_names_nothing(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    """A refusal that names the title is an advertisement."""
    token = await make_actor("tools-suggest@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/suggest_material",
        json={
            "tool": "suggest_material",
            "arguments": {"ref": str(uuid.uuid4()), "reason": "it follows on"},
        },
        headers=worker_headers(),
    )

    body = response.json()
    assert body["display"] is None
    assert "could not" in body["result"]


async def test_an_invented_argument_is_refused(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tools-bad-args@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/recall_history",
        json={"tool": "recall_history", "arguments": {"query": "x", "colour": "red"}},
        headers=worker_headers(),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "tool_arguments_invalid"


async def test_a_tool_nobody_defined_is_a_404(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tools-unknown@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/hypnotise",
        json={"tool": "hypnotise", "arguments": {}},
        headers=worker_headers(),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "unknown_tool"


async def test_a_finished_session_answers_no_tools(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tools-finished@example.com")
    session_id = await a_dashboard_session(client, token)
    await client.post(
        f"/api/worker/sessions/{session_id}/complete",
        json={"end_reason": "done", "usage": {}},
        headers=worker_headers(),
    )

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/remember",
        json={"tool": "remember", "arguments": {"fact": "too late"}},
        headers=worker_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "assistant_session_not_joinable"


async def test_the_tool_route_needs_the_worker_secret(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    token = await make_actor("tools-secret@example.com")
    session_id = await a_dashboard_session(client, token)
    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/remember",
        json={"tool": "remember", "arguments": {"fact": "x"}},
    )
    assert response.status_code == 401
