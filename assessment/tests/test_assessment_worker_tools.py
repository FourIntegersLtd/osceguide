"""Profile-named tools: check_time is the only one, and an unknown name is refused.

What matters is that naming a tool this worker cannot build fails loudly at
configuration time, rather than starting a session whose model has been
promised a tool that never answers; and that the clock comes from the pacing
plan the backend rendered, not from anything the worker decides.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from livekit_assessment_worker.tools import TOOL_BUILDERS, UnknownToolError, build_tools, session_clock

PACING = {
    "total_seconds": 600,
    "marks": [{"at_seconds": 150, "note": "[Notice: a quarter gone.]"}],
    "phases": [{"until_seconds": 600, "label": "working through the plan"}],
}


def _ctx():
    return SimpleNamespace(room=SimpleNamespace(local_participant=None))


def test_check_time_is_the_only_tool() -> None:
    assert sorted(TOOL_BUILDERS) == ["check_time"]


def test_no_names_means_no_tools() -> None:
    assert build_tools(_ctx(), (), {}, None) == []


def test_unknown_tool_name_is_a_configuration_error() -> None:
    with pytest.raises(UnknownToolError, match="not_a_tool"):
        build_tools(_ctx(), ("not_a_tool",), {}, None)


def test_the_retired_highlight_tool_is_gone() -> None:
    """Live debrief insights are removed; a profile naming the tool must fail."""
    with pytest.raises(UnknownToolError, match="highlight_lines"):
        build_tools(_ctx(), ("highlight_lines",), {"id_mapping": {"1": "m1"}}, None)


def test_no_pacing_plan_means_no_clock() -> None:
    assert session_clock({}) is None


def test_check_time_without_a_plan_is_a_configuration_error() -> None:
    with pytest.raises(UnknownToolError, match="check_time needs a pacing plan"):
        build_tools(_ctx(), ("check_time",), {}, session_clock({}))


def test_check_time_answers_from_the_plan_the_backend_sent() -> None:
    clock = session_clock({"pacing": PACING})
    [tool] = build_tools(_ctx(), ("check_time",), {"pacing": PACING}, clock)
    assert tool.info.name == "check_time"
    assert asyncio.run(tool(SimpleNamespace())) == "This has not started yet."
