"""What `app.core.llm` puts on the wire and how it falls over from Claude to OpenAI."""

from __future__ import annotations

from typing import Any

import pytest
from structlog.testing import capture_logs

from app.core.llm import (
    LlmReplyUnusable,
    NoModelKey,
    claude_reply,
    first_that_answers,
    json_object,
    openai_reply,
)
from tests.support.llm_fakes import install_fake_sdks


@pytest.mark.asyncio
async def test_the_request_has_no_temperature_or_tool_choice_and_caches_the_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = install_fake_sdks(monkeypatch, claude='{"a": 1}')

    text = await claude_reply(
        "k",
        system="Long stable prompt.",
        messages=[{"role": "user", "content": "go"}],
        max_tokens=16000,
        timeout=60,
        schema={"type": "object"},
        effort="low",
    )

    sent = providers.claude_sent
    assert text == '{"a": 1}'
    assert sent["model"] == "claude-sonnet-5-5"
    assert sent["system"] == [
        {"type": "text", "text": "Long stable prompt.", "cache_control": {"type": "ephemeral"}}
    ]
    assert sent["output_config"] == {
        "format": {"type": "json_schema", "schema": {"type": "object", "transformed": True}},
        "effort": "low",
    }
    assert not {"temperature", "tool_choice", "tools"} & set(sent)


@pytest.mark.asyncio
async def test_no_output_config_without_a_schema_or_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch)
    await claude_reply("k", system="s", messages=[], max_tokens=10, timeout=1)
    assert "output_config" not in providers.claude_sent


@pytest.mark.asyncio
@pytest.mark.parametrize(("stop", "text"), [("max_tokens", "{}"), ("refusal", "{}"), ("end_turn", "  ")])
async def test_a_cut_off_refused_or_empty_reply_is_refused(
    monkeypatch: pytest.MonkeyPatch, stop: str, text: str
) -> None:
    install_fake_sdks(monkeypatch, claude=text, claude_stop=stop)
    with pytest.raises(LlmReplyUnusable):
        await claude_reply("k", system="s", messages=[], max_tokens=10, timeout=1)


@pytest.mark.asyncio
async def test_a_schema_near_the_grammar_limit_is_warned_about(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_sdks(monkeypatch)
    big = {"type": "object", "description": "x" * 7000}
    with capture_logs() as logs:
        await claude_reply("k", system="s", messages=[], max_tokens=10, timeout=1, schema=big)
    assert [entry["event"] for entry in logs] == ["llm_schema_near_grammar_limit"]


@pytest.mark.asyncio
async def test_openai_reply_sends_the_turns_and_every_option_asked_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = install_fake_sdks(monkeypatch, openai='{"a": 2}')
    text = await openai_reply(
        "k",
        system="S",
        messages=[{"role": "user", "content": "U1"}, {"role": "assistant", "content": "A"}],
        model="m",
        timeout=5,
        max_tokens=77,
        reasoning_effort="none",
        response_format={"type": "json_object"},
    )
    assert text == '{"a": 2}'
    assert providers.openai_client == {"api_key": "k", "timeout": 5, "max_retries": 1}
    assert providers.openai_sent == {
        "model": "m",
        "messages": [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "U1"},
            {"role": "assistant", "content": "A"},
        ],
        "max_completion_tokens": 77,
        "reasoning_effort": "none",
        "response_format": {"type": "json_object"},
    }


@pytest.mark.asyncio
async def test_openai_reply_sends_only_the_turns_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch)
    await openai_reply("k", system="S", messages=[{"role": "user", "content": "U"}], model="m", timeout=5)
    assert providers.openai_sent == {
        "model": "m",
        "messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", ["", "  \n"])
async def test_an_empty_openai_reply_raises_so_the_next_provider_is_asked(
    monkeypatch: pytest.MonkeyPatch, empty: str
) -> None:
    install_fake_sdks(monkeypatch, openai=empty)
    with pytest.raises(LlmReplyUnusable):
        await openai_reply("k", system="S", messages=[], model="m", timeout=5)


@pytest.mark.asyncio
async def test_a_none_openai_reply_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_sdks(monkeypatch, openai=None)  # type: ignore[arg-type]
    with pytest.raises(LlmReplyUnusable):
        await openai_reply("k", system="S", messages=[], model="m", timeout=5)


async def _ok(key: str) -> str:
    return f"ok:{key}"


def _failing(message: str) -> Any:
    async def ask(_: str) -> str:
        raise RuntimeError(message)

    return ask


@pytest.mark.asyncio
async def test_first_that_answers_skips_blank_keys_and_falls_through() -> None:
    result = await first_that_answers([("a", " ", _ok), ("b", "k1", _failing("b down")), ("c", "k2", _ok)])
    assert result == "ok:k2"


@pytest.mark.asyncio
async def test_first_that_answers_raises_the_last_failure_and_needs_a_key() -> None:
    with pytest.raises(RuntimeError, match="c down"):
        await first_that_answers([("b", "k1", _failing("b down")), ("c", "k2", _failing("c down"))])
    with pytest.raises(NoModelKey):
        await first_that_answers([("a", "", _ok)])


def test_json_object_finds_a_fenced_object_and_rejects_the_rest() -> None:
    assert json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert json_object("no json") is None
    assert json_object("{broken}") is None
