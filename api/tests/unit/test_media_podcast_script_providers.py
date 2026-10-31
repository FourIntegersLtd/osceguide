"""The podcast script is written by Claude first and OpenAI second."""

from __future__ import annotations

import pytest

from app.core.settings import Settings
from app.features.media_production import podcast_script
from tests.support.llm_fakes import install_fake_sdks

_BOTH = Settings(anthropic_api_key="a", openai_api_key="o")


def test_claude_writes_first_at_low_effort_without_temperature_or_forced_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = install_fake_sdks(monkeypatch, claude="Ben: Claude.")

    script = podcast_script.generate_script(_BOTH, "Asthma.")

    sent = providers.claude_sent
    assert (script, providers.asked) == ("Ben: Claude.", ["claude"])
    assert sent["model"] == "claude-sonnet-5-5"
    assert sent["max_tokens"] >= 16000
    assert sent["output_config"] == {"effort": "low"}
    assert not {"temperature", "tool_choice"} & set(sent)
    assert providers.claude_client["timeout"] == 150


def test_openai_writes_when_claude_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude=RuntimeError("anthropic down"), openai="Ben: OpenAI.")

    script = podcast_script.generate_script(_BOTH, "Asthma.")

    assert (script, providers.asked) == ("Ben: OpenAI.", ["claude", "openai"])


@pytest.mark.parametrize("stop", ["max_tokens", "refusal"])
def test_a_cut_off_claude_script_comes_from_openai(monkeypatch: pytest.MonkeyPatch, stop: str) -> None:
    providers = install_fake_sdks(
        monkeypatch, claude="Ben: Half a scr", claude_stop=stop, openai="Ben: Whole."
    )

    script = podcast_script.generate_script(_BOTH, "Asthma.")

    assert (script, providers.asked) == ("Ben: Whole.", ["claude", "openai"])


def test_an_empty_claude_script_comes_from_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, claude="", openai="Ben: Whole.")

    assert podcast_script.generate_script(_BOTH, "Asthma.") == "Ben: Whole."
    assert providers.asked == ["claude", "openai"]


def test_openai_writes_when_the_anthropic_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = install_fake_sdks(monkeypatch, openai="Ben: OpenAI.")

    script = podcast_script.generate_script(Settings(openai_api_key="o"), "Asthma.")

    assert (script, providers.asked) == ("Ben: OpenAI.", ["openai"])
