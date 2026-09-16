"""Profile-named tools: none are implemented, and an unknown name is refused.

The worker implements no function tools. The seam is still tested because the
profile contract can still name one: what matters now is that naming a tool
this worker cannot build fails loudly at configuration time, rather than
starting a session whose model has been promised a tool that never answers.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from livekit_assessment_worker.tools import TOOL_BUILDERS, UnknownToolError, build_tools


def _ctx():
    return SimpleNamespace(room=SimpleNamespace(local_participant=None))


def test_the_worker_implements_no_tools() -> None:
    assert TOOL_BUILDERS == {}


def test_no_names_means_no_tools() -> None:
    assert build_tools(_ctx(), (), {}) == []


def test_unknown_tool_name_is_a_configuration_error() -> None:
    with pytest.raises(UnknownToolError, match="not_a_tool"):
        build_tools(_ctx(), ("not_a_tool",), {})


def test_the_retired_highlight_tool_is_gone() -> None:
    """Live debrief insights are removed; a profile naming the tool must fail."""
    with pytest.raises(UnknownToolError, match="highlight_lines"):
        build_tools(_ctx(), ("highlight_lines",), {"id_mapping": {"1": "m1"}})
