"""Profile-named tools: built from the tool context, unknown names refused, highlights published."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from livekit_assessment_worker import tools as tools_module
from livekit_assessment_worker.tools import HIGHLIGHT_LINES, UnknownToolError, build_tools, highlight_payload


class _Publisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.published: list[tuple[dict, bool]] = []
        self.fail = fail

    async def publish_data(self, data: bytes, *, reliable: bool) -> None:
        if self.fail:
            raise RuntimeError("no room")
        self.published.append((json.loads(data), reliable))


def _ctx(publisher: _Publisher):
    return SimpleNamespace(room=SimpleNamespace(local_participant=publisher))


def test_no_names_means_no_tools() -> None:
    assert build_tools(_ctx(_Publisher()), (), {}) == []


def test_unknown_tool_name_is_a_configuration_error() -> None:
    with pytest.raises(UnknownToolError, match="not_a_tool"):
        build_tools(_ctx(_Publisher()), ("not_a_tool",), {})


def test_highlight_payload_translates_line_ids_and_drops_unknown_ones(caplog) -> None:
    payload = highlight_payload({"1": "uuid-1", "2": "uuid-2"}, ["1", "9", "2"], ["Ask open questions"])
    assert payload == {"transcript_message_ids": ["uuid-1", "uuid-2"], "recommendations": ["Ask open questions"]}
    assert "1 of 3 line ids not in the mapping" in caplog.text


def test_highlight_lines_tool_publishes_translated_ids_reliably(monkeypatch) -> None:
    captured = {}

    def fake_function_tool(fn, *, name, description):
        captured["name"], captured["fn"] = name, fn
        return fn

    monkeypatch.setattr(tools_module, "function_tool", fake_function_tool)
    publisher = _Publisher()
    (tool,) = build_tools(_ctx(publisher), (HIGHLIGHT_LINES,), {"id_mapping": {"1": "uuid-1", 2: "uuid-2"}})
    assert captured["name"] == HIGHLIGHT_LINES and tool is captured["fn"]

    result = asyncio.run(tool(None, ["Summarise the plan"], ["1", "2"]))
    assert result == "Successfully sent feedback"
    assert publisher.published == [({"transcript_message_ids": ["uuid-1", "uuid-2"], "recommendations": ["Summarise the plan"]}, True)]


def test_highlight_lines_tells_the_model_when_publishing_fails(monkeypatch) -> None:
    monkeypatch.setattr(tools_module, "function_tool", lambda fn, **_: fn)
    (tool,) = build_tools(_ctx(_Publisher(fail=True)), (HIGHLIGHT_LINES,), {"id_mapping": {"1": "uuid-1"}})
    assert "verbally" in asyncio.run(tool(None, ["Summarise the plan"], ["1"]))


def test_highlight_payload_without_line_ids_still_carries_the_recommendations() -> None:
    """A debrief with no transcript has no ids to anchor to; the written panel must still fill."""
    assert highlight_payload({}, None, ["Safety-net the red flags"]) == {
        "transcript_message_ids": [],
        "recommendations": ["Safety-net the red flags"],
    }


def test_highlight_lines_tool_may_be_called_with_recommendations_alone(monkeypatch) -> None:
    monkeypatch.setattr(tools_module, "function_tool", lambda fn, **_: fn)
    publisher = _Publisher()
    (tool,) = build_tools(_ctx(publisher), (HIGHLIGHT_LINES,), {})

    assert asyncio.run(tool(None, ["Opened with an open question"])) == "Successfully sent feedback"
    assert publisher.published == [
        ({"transcript_message_ids": [], "recommendations": ["Opened with an open question"]}, True)
    ]
