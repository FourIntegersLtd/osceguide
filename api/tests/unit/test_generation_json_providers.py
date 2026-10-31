"""JSON generation asks Claude first and OpenAI second."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.settings import Settings
from app.features.generation import service as generation
from app.features.generation.errors import GenerationUnavailable
from tests.support.llm_fakes import install_fake_sdks


async def _ask(settings: Settings) -> dict[str, Any]:
    return await generation._json_completion(settings=settings, system="S", user="U")


@pytest.mark.asyncio
async def test_claude_answers_first_even_when_it_fences_the_json(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude='```json\n{"from": "claude"}\n```')

    result = await _ask(Settings(anthropic_api_key="a", openai_api_key="o"))

    sent = providers.claude_sent
    assert (result, providers.asked) == ({"from": "claude"}, ["claude"])
    assert sent["model"] == "claude-sonnet-5-5"
    assert not {"temperature", "tool_choice"} & set(sent)


@pytest.mark.asyncio
@pytest.mark.parametrize("claude_text", [RuntimeError("anthropic down"), "not json at all", "[1, 2]"])
async def test_openai_answers_when_claude_fails_or_is_not_an_object(
    monkeypatch: pytest.MonkeyPatch, claude_text: str | Exception
) -> None:
    providers = install_fake_sdks(monkeypatch, claude=claude_text, openai='{"from": "openai"}')

    result = await _ask(Settings(anthropic_api_key="a", openai_api_key="o"))

    assert (result, providers.asked) == ({"from": "openai"}, ["claude", "openai"])


@pytest.mark.asyncio
async def test_openai_answers_when_the_anthropic_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude='{"from": "claude"}', openai='{"from": "openai"}')

    assert await _ask(Settings(openai_api_key="o")) == {"from": "openai"}
    assert providers.asked == ["openai"]


@pytest.mark.asyncio
async def test_claude_down_with_no_openai_key_says_the_model_did_not_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_sdks(monkeypatch, claude=RuntimeError("anthropic down"))
    with pytest.raises(GenerationUnavailable) as raised:
        await _ask(Settings(anthropic_api_key="a"))
    assert raised.value.message == "The model did not answer; try again"


@pytest.mark.asyncio
async def test_no_key_at_all_says_generation_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_sdks(monkeypatch)
    with pytest.raises(GenerationUnavailable) as raised:
        await _ask(Settings())
    assert raised.value.message == "Content generation is not configured on this environment"


@pytest.mark.asyncio
async def test_a_reply_that_is_not_an_object_keeps_its_own_message(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_sdks(monkeypatch, claude=RuntimeError("down"), openai="not json")
    with pytest.raises(GenerationUnavailable) as raised:
        await _ask(Settings(anthropic_api_key="a", openai_api_key="o"))
    assert raised.value.message == "Model did not return a JSON object"


@pytest.mark.asyncio
async def test_openai_is_asked_for_a_json_object_with_the_one_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude=RuntimeError("down"), openai='{"from": "openai"}')

    await _ask(Settings(anthropic_api_key="a", openai_api_key="o"))

    sent = providers.openai_sent
    assert sent["model"] == "gpt-6.1-sol"
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["messages"] == [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
