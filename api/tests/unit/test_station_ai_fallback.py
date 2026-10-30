"""The Claude fallback for station generation must not force a tool: claude-sonnet-5-5 answers 400 to it."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from app.core.settings import Settings
from app.features.stations import station_ai


class _Answer(BaseModel):
    title: str


@pytest.mark.asyncio
async def test_fallback_asks_for_the_tool_without_forcing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The request forces no `tool_choice`, names the tool in the system line, and parses."""
    sent: dict[str, Any] = {}

    class _Messages:
        async def create(self, **kwargs: Any) -> Any:
            sent.update(kwargs)
            block = SimpleNamespace(type="tool_use", input={"title": "Chest pain"})
            return SimpleNamespace(stop_reason="tool_use", content=[block])

    fake = ModuleType("anthropic")
    fake.AsyncAnthropic = lambda **_: SimpleNamespace(messages=_Messages())  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    parsed, err = await station_ai._parse_with_anthropic(
        [{"role": "system", "content": "Write stations."}, {"role": "user", "content": "Chest pain."}],
        _Answer,
        settings=Settings(anthropic_api_key="k"),
        model=station_ai.STATION_AUTOGENERATE_FALLBACK_MODEL,
        log_prefix="t",
    )

    assert (parsed, err) == (_Answer(title="Chest pain"), "")
    assert sent["model"] == "claude-sonnet-5-5"
    assert "tool_choice" not in sent
    assert sent["system"] == "Write stations.\n\nAnswer by calling emit_result."
