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
from tests.support.fakes import FakeMaterialIndex, FakeTutorPromptRenderer
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


async def test_searching_material_with_no_index_says_it_cannot_look_it_up(
    client: AsyncClient, make_actor, tutor_renderer: FakeTutorPromptRenderer
) -> None:  # type: ignore[no-untyped-def]
    """A deployment with no embedding key must not claim it searched.

    The test environment has no `OPENAI_API_KEY`, so this is the real path a
    deployment without one takes. "I could not look that up" and "the material
    does not say" are different claims, and the tutor speaks both aloud with
    the same confidence.
    """
    from app.features.tutor_memory import service_search

    token = await make_actor("tools-search@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/search_material",
        json={"tool": "search_material", "arguments": {"query": "asthma management"}},
        headers=worker_headers(),
    )

    assert response.json()["result"] == service_search.NOT_CONFIGURED


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


# --------------------------------------------------------------------------
# Searching the material. The index is faked here: which passage is nearest is
# the adapter's business and is proved against real pgvector in
# `tests/repository/test_material_index.py`. What this file owns is that the
# entitlement decides what may be searched, and what the worker is handed back.
# --------------------------------------------------------------------------


@pytest.fixture
def material(monkeypatch: pytest.MonkeyPatch) -> FakeMaterialIndex:
    """Put a fake index behind `search_material`.

    Through the service's own optional `index` argument, which exists for this,
    rather than by patching the builder — the same seam the renderer fixture
    above uses.
    """
    from app.features.tutor_memory import service_tools

    fake = FakeMaterialIndex()
    original = service_tools.run

    async def with_fake(session, **kwargs):  # type: ignore[no-untyped-def]
        return await original(session, index=fake, **kwargs)

    monkeypatch.setattr(service_tools, "run", with_fake)
    return fake


async def entitled_actor(
    session: AsyncSession,
    make_actor,
    email: str,
    code: str = "sca",  # type: ignore[no-untyped-def]
) -> tuple[str, uuid.UUID]:
    """A signed-in doctor who holds one exam, and that exam's id."""
    from datetime import UTC, datetime, timedelta

    from app.features.entitlements import repository as ent_repo
    from app.features.identity import repository as identity_repo
    from tests.support.catalog import ensure_exam

    token = await make_actor(email)
    user = await identity_repo.user_by_email(session, email)
    assert user is not None
    exam = await ensure_exam(session, code)
    assert exam is not None
    await ent_repo.grant(
        session,
        user_id=user.id,
        exam_id=exam.id,
        source="purchase",
        ends_at=datetime.now(UTC) + timedelta(days=30),
    )
    await session.flush()
    return token, exam.id


async def search_for(client: AsyncClient, session_id: str, query: str) -> dict:  # type: ignore[type-arg]
    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/search_material",
        json={"tool": "search_material", "arguments": {"query": query}},
        headers=worker_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


async def test_a_search_answers_from_the_material_and_cites_it(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,  # type: ignore[no-untyped-def]
    tutor_renderer: FakeTutorPromptRenderer,
    material: FakeMaterialIndex,
) -> None:
    token, exam_id = await entitled_actor(db_session, make_actor, "tools-hit@example.com")
    await material.upsert(
        corpus="summary",
        source_id="sum-1",
        exam_id=str(exam_id),
        title="Chest pain",
        chunks=[{"index": 0, "section": "red_flags", "text": "Safety net chest pain in writing."}],
    )
    session_id = await a_dashboard_session(client, token)

    body = await search_for(client, session_id, "safety net")

    # The passage travels in the spoken half so the tutor can answer from it,
    # numbered so it can refer to one without reading a title aloud.
    assert "[1] Safety net chest pain in writing." in body["result"]
    card = body["display"]
    assert card["card"] == "citations"
    assert card["citations"] == [
        {
            "n": 1,
            "title": "Chest pain",
            "section": "red_flags",
            "ref": {"kind": "summary", "id": "sum-1", "slug": None},
        }
    ]


async def test_a_search_never_reaches_material_from_an_exam_they_do_not_hold(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,  # type: ignore[no-untyped-def]
    tutor_renderer: FakeTutorPromptRenderer,
    material: FakeMaterialIndex,
) -> None:
    """Today the A to Z and the slides are gated in the browser only.

    A tutor that read out of them would be a way round that gate, so the gate
    is server-side here: the entitled exams are worked out from the grants and
    handed to the index as a filter.
    """
    from tests.support.catalog import ensure_exam

    token, held = await entitled_actor(db_session, make_actor, "tools-locked@example.com")
    other = await ensure_exam(db_session, "plab")
    assert other is not None
    await material.upsert(
        corpus="summary",
        source_id="locked",
        exam_id=str(other.id),
        title="Something they have not bought",
        chunks=[{"index": 0, "section": "management", "text": "Locked advice about asthma."}],
    )
    session_id = await a_dashboard_session(client, token)

    body = await search_for(client, session_id, "asthma")

    from app.features.tutor_memory import service_search

    assert body["result"] == service_search.NOTHING_IN_MATERIAL
    assert body["display"] is None
    # The refusal names nothing: a locked title read aloud is an advertisement.
    assert "Something they have not bought" not in body["result"]
    # And the index was asked only about the exam they hold.
    assert material.searches[-1][1] == (str(held),)


async def test_holding_no_exam_at_all_searches_nothing(
    client: AsyncClient,
    make_actor,  # type: ignore[no-untyped-def]
    tutor_renderer: FakeTutorPromptRenderer,
    material: FakeMaterialIndex,
) -> None:
    """No grants is not an empty filter, which would search everything."""
    from app.features.tutor_memory import service_search

    token = await make_actor("tools-nogrant@example.com")
    session_id = await a_dashboard_session(client, token)

    body = await search_for(client, session_id, "asthma")

    assert body["result"] == service_search.NOTHING_IN_MATERIAL
    assert material.searches == []


async def test_a_search_can_be_narrowed_to_one_kind_of_material(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,  # type: ignore[no-untyped-def]
    tutor_renderer: FakeTutorPromptRenderer,
    material: FakeMaterialIndex,
) -> None:
    token, exam_id = await entitled_actor(db_session, make_actor, "tools-kind@example.com")
    session_id = await a_dashboard_session(client, token)

    response = await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/search_material",
        json={
            "tool": "search_material",
            "arguments": {"query": "asthma", "kind": "slide_deck"},
        },
        headers=worker_headers(),
    )

    assert response.status_code == 200, response.text
    assert material.searches[-1][2] == "slide_deck"


async def test_asking_for_any_kind_does_not_narrow_the_corpus(
    client: AsyncClient,
    db_session: AsyncSession,
    make_actor,  # type: ignore[no-untyped-def]
    tutor_renderer: FakeTutorPromptRenderer,
    material: FakeMaterialIndex,
) -> None:
    """`any` is the model's word for "no preference", not a corpus name."""
    token, _ = await entitled_actor(db_session, make_actor, "tools-any@example.com")
    session_id = await a_dashboard_session(client, token)

    await client.post(
        f"/api/worker/assistant-sessions/{session_id}/tools/search_material",
        json={"tool": "search_material", "arguments": {"query": "asthma", "kind": "any"}},
        headers=worker_headers(),
    )

    assert material.searches[-1][2] is None
