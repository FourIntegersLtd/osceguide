"""The worker and the browser hold the same wire contract in two files.

Nothing enforced that before: a rename on one side was found in a room, not in
CI. This reads the TypeScript and checks the constants agree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from livekit_assistant_worker.ui_guidance import contracts

# The frontend is a separate repository checked out beside this one. When it is
# not there, there is nothing to drift against.
CONTRACTS_TS = Path(__file__).resolve().parents[2] / "web/src/foundation/livekit/guidance/contracts.ts"

_STRING_CONST = re.compile(r'export const (\w+)\s*=\s*"([^"]*)"\s*as const;')
_NUMBER_CONST = re.compile(r"export const (\w+)\s*=\s*(\d+);")


def _typescript_constants() -> dict[str, str | int]:
    if not CONTRACTS_TS.exists():
        pytest.skip(f"web/ not present in this checkout ({CONTRACTS_TS})")
    source = CONTRACTS_TS.read_text()
    found: dict[str, str | int] = {name: value for name, value in _STRING_CONST.findall(source)}
    found.update({name: int(value) for name, value in _NUMBER_CONST.findall(source)})
    return found


SHARED_NAMES = (
    "RPC_METHOD_SCREENSHOT_CHUNKED",
    "RPC_METHOD_PERFORM_CLICK",
    "RPC_METHOD_SCROLL",
    "DATA_TYPE_SCREENSHOT_CHUNK",
    "DATA_TYPE_NAV_MODE_CHOICE",
    "DATA_TYPE_NAV_MODE_PROMPT",
    "DATA_TYPE_GUIDANCE_PROGRESS",
    "DATA_TYPE_ASSISTANT_CARD",
    "POINTER_MESSAGE_TYPE",
    "TOOL_RUNNING_MESSAGE_TYPE",
    "UI_GUIDANCE_SCHEMA_VERSION",
    "PROGRESS_STEP_CAPTURING",
    "PROGRESS_STEP_READING",
    "PROGRESS_STEP_ACTING",
    "PROGRESS_STEP_DONE",
)


@pytest.mark.parametrize("name", SHARED_NAMES)
def test_both_sides_agree_on(name: str) -> None:
    typescript = _typescript_constants()

    assert name in typescript, f"{name} is missing from contracts.ts"
    assert typescript[name] == getattr(contracts, name)


def test_the_python_side_names_every_step_the_panel_can_show() -> None:
    assert contracts.PROGRESS_STEPS == (
        contracts.PROGRESS_STEP_CAPTURING,
        contracts.PROGRESS_STEP_READING,
        contracts.PROGRESS_STEP_ACTING,
        contracts.PROGRESS_STEP_DONE,
    )
