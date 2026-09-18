"""Tools the backend defines: the worker carries the schema and forwards the call."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import pytest
from livekit.agents.llm.tool_context import get_raw_function_info, is_raw_function_tool
from voice_infra import BackendRegistry
from voice_infra.backend_http import SyncGetResult
from voice_infra.config import BACKENDS_ENV

from livekit_assistant_worker.bootstrap import BootstrapError, RemoteTool, parse_bootstrap
from livekit_assistant_worker.tools import remote

from _worker_fakes import FakeRoom

SPEC = {"practice": {"base_url_env": "PRACTICE_URL", "secret_env": "PRACTICE_SECRET", "secret_header": "X-S", "slot_release_path": "/r", "slot_extend_path": "/e", "slot_payload_key": "room_name"}}
LOOKUP = {"name": "lookup_notes", "description": "Find a note.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}
SHOW = {"name": "show_item", "description": "Show something.", "parameters": {"type": "object", "properties": {"ref": {"type": "string"}}}}
SESSION = {"session_id": "unified_1", "worker_type": "dashboard", "instructions": "Rendered."}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv(BACKENDS_ENV, json.dumps(SPEC))
    monkeypatch.setenv("PRACTICE_URL", "https://api.test")
    monkeypatch.setenv("PRACTICE_SECRET", "s3cret")


def _endpoints():
    return BackendRegistry.from_env().get("practice")


def _tools(*specs: dict, room: FakeRoom | None = None):
    room = room or FakeRoom()
    from livekit_assistant_worker.ui_guidance.browser import BrowserChannel

    return remote.build_remote_tools(_endpoints(), "unified_1", [RemoteTool(**s) for s in specs], publish=BrowserChannel(room).publish), room


def _call(tool, arguments: dict):
    return asyncio.run(tool(raw_arguments=arguments, context=None))


def test_the_schema_the_model_sees_is_the_backends_own() -> None:
    tools, _ = _tools(LOOKUP, SHOW)
    assert [is_raw_function_tool(t) for t in tools] == [True, True]
    infos = [get_raw_function_info(t) for t in tools]
    assert [i.name for i in infos] == ["lookup_notes", "show_item"]
    assert infos[0].raw_schema == LOOKUP


def test_a_call_is_posted_to_the_backend_and_its_text_returned() -> None:
    tools, _ = _tools(LOOKUP)
    with patch.object(remote, "sync_post_json", return_value=SyncGetResult(ok=True, status=200, data={"result": "Two notes found."})) as post:
        assert _call(tools[0], {"query": "chest pain"}) == "Two notes found."
    base_url, path, payload = post.call_args.args
    assert (base_url, path) == ("https://api.test", "/api/worker/assistant-sessions/unified_1/tools/lookup_notes")
    assert payload["tool"] == "lookup_notes" and payload["arguments"] == {"query": "chest pain"} and payload["call_id"]
    assert post.call_args.kwargs["headers"] == {"X-S": "s3cret"}
    assert post.call_args.kwargs["timeout"] == remote.REMOTE_TOOL_TIMEOUT_S


def test_what_the_backend_wants_shown_reaches_the_browser_unchanged() -> None:
    tools, room = _tools(SHOW)
    card = {"type": "assistant_card", "schemaVersion": 2, "card": "suggestion", "ref": {"kind": "station", "id": "sv-1"}, "title": "Anxiety"}
    with patch.object(remote, "sync_post_json", return_value=SyncGetResult(ok=True, status=200, data={"result": "Shown.", "display": card})):
        assert _call(tools[0], {"ref": "sv-1"}) == "Shown."
    assert room.local_participant.published == [card]


def test_nothing_is_published_when_the_backend_returns_no_display() -> None:
    tools, room = _tools(SHOW)
    with patch.object(remote, "sync_post_json", return_value=SyncGetResult(ok=True, status=200, data={"result": "Shown.", "display": None})):
        _call(tools[0], {})
    assert room.local_participant.published == []


@pytest.mark.parametrize(
    "outcome",
    [SyncGetResult(ok=False, status=500, data=None), SyncGetResult(ok=True, status=200, data={"result": ""}), SyncGetResult(ok=True, status=200, data={"error": "x"})],
    ids=["http-error", "blank-result", "no-result-key"],
)
def test_a_failed_lookup_gives_the_model_a_line_it_can_say(outcome: SyncGetResult) -> None:
    tools, _ = _tools(LOOKUP)
    with patch.object(remote, "sync_post_json", return_value=outcome):
        assert _call(tools[0], {"query": "x"}) == remote.TOOL_UNAVAILABLE


def test_a_transport_failure_does_the_same() -> None:
    tools, _ = _tools(LOOKUP)
    with patch.object(remote, "sync_post_json", side_effect=OSError("down")):
        assert _call(tools[0], {"query": "x"}) == remote.TOOL_UNAVAILABLE


def test_a_bootstrap_without_tools_parses_as_before() -> None:
    assert parse_bootstrap({"session": SESSION}).tools == ()


def test_the_bootstrap_carries_tools_in_the_backends_order() -> None:
    session = parse_bootstrap({"session": {**SESSION, "tools": [SHOW, LOOKUP]}})
    assert [t.name for t in session.tools] == ["show_item", "lookup_notes"]


@pytest.mark.parametrize(
    "tools",
    [
        [LOOKUP, LOOKUP],
        [{**LOOKUP, "name": "Lookup Notes"}],
        [{**LOOKUP, "description": ""}],
        [{**LOOKUP, "parameters": {"type": "string"}}],
    ],
    ids=["duplicate", "bad-name", "no-description", "not-an-object-schema"],
)
def test_a_malformed_tool_list_is_refused_at_bootstrap(tools: list[dict]) -> None:
    with pytest.raises(BootstrapError):
        parse_bootstrap({"session": {**SESSION, "tools": tools}})
