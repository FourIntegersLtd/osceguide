"""Claude answers station generation first, OpenAI second; Claude is never forced or heated."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.core.settings import Settings
from app.features.stations import station_ai
from tests.support.llm_fakes import Providers, install_fake_sdks


class _Answer(BaseModel):
    title: str


_MESSAGES = [{"role": "system", "content": "Write stations."}, {"role": "user", "content": "Chest pain."}]


def _wire(
    monkeypatch: pytest.MonkeyPatch, *, claude: str | Exception, openai: _Answer | Exception
) -> Providers:
    """Fake both SDKs; OpenAI answers through its beta `parse`.

    The returned record lists which providers were asked, in order.
    """
    return install_fake_sdks(monkeypatch, claude=claude, openai_parsed=openai)


_CLAUDE_OK = '{"title": "From Claude"}'
_CLAUDE_DOWN = RuntimeError("anthropic down")


@pytest.mark.asyncio
async def test_claude_answers_first_and_openai_is_not_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _wire(monkeypatch, claude=_CLAUDE_OK, openai=_Answer(title="From OpenAI")).asked
    settings = Settings(anthropic_api_key="a", openai_api_key="o")

    parsed, err = await station_ai.parse_ai_structured(_MESSAGES, _Answer, settings=settings)

    assert (parsed, err, asked) == (_Answer(title="From Claude"), "", ["claude"])


@pytest.mark.asyncio
async def test_openai_answers_when_claude_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _wire(monkeypatch, claude=_CLAUDE_DOWN, openai=_Answer(title="From OpenAI")).asked
    settings = Settings(anthropic_api_key="a", openai_api_key="o")

    parsed, err = await station_ai.parse_ai_structured(_MESSAGES, _Answer, settings=settings)

    assert (parsed, err, asked) == (_Answer(title="From OpenAI"), "", ["claude", "openai"])


@pytest.mark.asyncio
async def test_openai_answers_when_the_anthropic_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _wire(monkeypatch, claude=_CLAUDE_OK, openai=_Answer(title="From OpenAI")).asked

    parsed, _ = await station_ai.parse_ai_structured(
        _MESSAGES, _Answer, settings=Settings(openai_api_key="o")
    )

    assert (parsed, asked) == (_Answer(title="From OpenAI"), ["openai"])


@pytest.mark.asyncio
async def test_claude_off_schema_reply_falls_through_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _wire(monkeypatch, claude='{"headline": "no title"}', openai=_Answer(title="From OpenAI")).asked

    parsed, _ = await station_ai.parse_ai_structured(
        _MESSAGES, _Answer, settings=Settings(anthropic_api_key="a", openai_api_key="o")
    )

    assert (parsed, asked) == (_Answer(title="From OpenAI"), ["claude", "openai"])


@pytest.mark.asyncio
async def test_a_double_failure_reports_claudes_error_not_openais(monkeypatch: pytest.MonkeyPatch) -> None:
    _wire(monkeypatch, claude=_CLAUDE_DOWN, openai=station_ai._ParseFailed("openai down"))

    parsed, err = await station_ai.parse_ai_structured(
        _MESSAGES, _Answer, settings=Settings(anthropic_api_key="a", openai_api_key="o")
    )

    assert (parsed, err) == (None, "anthropic down")


@pytest.mark.asyncio
async def test_claude_is_sent_the_schema_without_temperature_or_forced_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = install_fake_sdks(monkeypatch, claude='{"title": "x"}')
    await station_ai.parse_ai_structured(_MESSAGES, _Answer, settings=Settings(anthropic_api_key="a"))

    sent = providers.claude_sent
    assert sent["model"] == "claude-sonnet-5-5"
    assert sent["system"][0]["text"] == "Write stations."
    assert sent["output_config"]["format"]["schema"]["properties"]["title"]["type"] == "string"
    assert sent["max_tokens"] >= 16000
    assert not {"temperature", "tool_choice"} & set(sent)


@pytest.mark.asyncio
async def test_openai_is_sent_the_messages_and_the_response_model(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = _wire(monkeypatch, claude=_CLAUDE_DOWN, openai=_Answer(title="From OpenAI"))

    await station_ai.parse_ai_structured(
        _MESSAGES, _Answer, settings=Settings(anthropic_api_key="a", openai_api_key="o")
    )

    assert providers.openai_parse_sent == {
        "model": "gpt-6.1-sol",
        "messages": _MESSAGES,
        "response_format": _Answer,
        "timeout": 480,
    }
