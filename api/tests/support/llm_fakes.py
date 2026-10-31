"""Fake `anthropic` and `openai` SDKs, so a test reads the literal request `app.core.llm` sends."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


@dataclass
class Providers:
    """Which providers were asked, in order, the last request each was sent, and how each client was built."""

    asked: list[str] = field(default_factory=list)
    claude_sent: dict[str, Any] = field(default_factory=dict)
    openai_sent: dict[str, Any] = field(default_factory=dict)
    openai_parse_sent: dict[str, Any] = field(default_factory=dict)
    claude_client: dict[str, Any] = field(default_factory=dict)
    openai_client: dict[str, Any] = field(default_factory=dict)


class _Client:
    """An SDK client usable as `async with`, answering through `create`."""

    def __init__(self, **namespaces: Any) -> None:
        self.__dict__.update(namespaces)

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


def install_fake_sdks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    claude: str | Exception = "Claude.",
    claude_stop: str = "end_turn",
    openai: str = "OpenAI.",
    openai_parsed: Any = None,
) -> Providers:
    """Replace both SDKs. `claude` is the reply text, or the exception Claude raises;
    `openai_parsed` is what OpenAI's beta `parse` returns, or the exception it raises."""
    providers = Providers()

    async def claude_create(**kwargs: Any) -> Any:
        providers.asked.append("claude")
        providers.claude_sent = kwargs
        if isinstance(claude, Exception):
            raise claude
        return SimpleNamespace(stop_reason=claude_stop, content=[SimpleNamespace(type="text", text=claude)])

    async def openai_create(**kwargs: Any) -> Any:
        providers.asked.append("openai")
        providers.openai_sent = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=openai))])

    async def openai_parse(**kwargs: Any) -> Any:
        providers.asked.append("openai")
        providers.openai_parse_sent = kwargs
        if isinstance(openai_parsed, Exception):
            raise openai_parsed
        message = SimpleNamespace(parsed=openai_parsed, refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])

    anthropic = ModuleType("anthropic")

    def claude_client(**kwargs: Any) -> _Client:
        providers.claude_client = kwargs
        return _Client(messages=SimpleNamespace(create=claude_create))

    def openai_client(**kwargs: Any) -> _Client:
        providers.openai_client = kwargs
        return _Client(
            chat=SimpleNamespace(completions=SimpleNamespace(create=openai_create)),
            beta=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=openai_parse))),
        )

    anthropic.AsyncAnthropic = claude_client  # type: ignore[attr-defined]
    anthropic.transform_schema = lambda schema: {**schema, "transformed": True}  # type: ignore[attr-defined]
    openai_sdk = ModuleType("openai")
    openai_sdk.AsyncOpenAI = openai_client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", anthropic)
    monkeypatch.setitem(sys.modules, "openai", openai_sdk)
    return providers
