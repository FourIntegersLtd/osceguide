"""The assistant's written answers: Claude first, OpenAI second."""

from types import SimpleNamespace

import pytest

from app.features.assistant import service_llm
from tests.support.llm_fakes import install_fake_sdks

MESSAGES = [{"role": "user", "content": "How do I book a mock?"}]


def _settings(anthropic_key: str = "a", openai_key: str = "o") -> SimpleNamespace:
    return SimpleNamespace(anthropic_api_key=anthropic_key, openai_api_key=openai_key)


async def _ask(settings: SimpleNamespace) -> str:
    return await service_llm.complete(settings, "SYSTEM", MESSAGES, max_tokens=500)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_claude_answers_first_and_is_sent_the_literal_request(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude="From Claude")

    assert await _ask(_settings()) == "From Claude"
    assert providers.asked == ["claude"]
    sent = providers.claude_sent
    assert sent["model"] == "claude-haiku-5-5"
    assert sent["max_tokens"] == 500
    assert "temperature" not in sent and "tool_choice" not in sent
    assert sent["output_config"] == {"effort": "low"}
    assert sent["system"] == [{"type": "text", "text": "SYSTEM", "cache_control": {"type": "ephemeral"}}]
    assert sent["messages"] == MESSAGES


@pytest.mark.asyncio
async def test_an_error_from_claude_falls_back_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude=RuntimeError("400"), openai="From OpenAI")

    assert await _ask(_settings()) == "From OpenAI"
    sent = providers.openai_sent
    assert sent["model"] == "gpt-6-luna"
    assert sent["reasoning_effort"] == "low" and sent["max_completion_tokens"] == 500
    assert sent["messages"] == [{"role": "system", "content": "SYSTEM"}, *MESSAGES]


@pytest.mark.asyncio
async def test_a_missing_anthropic_key_goes_straight_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, openai="From OpenAI")

    assert await _ask(_settings(anthropic_key=" ")) == "From OpenAI"
    assert providers.asked == ["openai"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stop", ["max_tokens", "refusal"])
async def test_a_cut_off_or_refused_claude_answer_falls_back(
    monkeypatch: pytest.MonkeyPatch, stop: str
) -> None:
    providers = install_fake_sdks(
        monkeypatch, claude="I can't help with that", claude_stop=stop, openai="From OpenAI"
    )

    assert await _ask(_settings()) == "From OpenAI"
    assert providers.asked == ["claude", "openai"]


@pytest.mark.asyncio
async def test_no_key_or_only_failures_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_sdks(monkeypatch)
    with pytest.raises(service_llm.ModelUnavailable):
        await _ask(_settings("", ""))
    install_fake_sdks(monkeypatch, claude=RuntimeError("down"), openai="")
    with pytest.raises(service_llm.ModelUnavailable):
        await _ask(_settings())
