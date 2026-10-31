"""Recovering doctor and patient turns from one mixed recording.

The recovery itself is a model call; what is worth testing without one is what
this slice does with the answer, because every one of these is a way somebody
else's words end up marked as the candidate's.
"""

from __future__ import annotations

import pytest

from app.core.ports import Transcriber, TranscriptionFailed
from app.core.settings import Settings
from app.features.peer_practice import diariser
from tests.support.fakes import FakeTranscriber
from tests.support.llm_fakes import install_fake_sdks


def test_the_transcriber_double_conforms_to_the_port() -> None:
    assert isinstance(FakeTranscriber(), Transcriber)


def test_turns_keep_their_order_and_their_speakers() -> None:
    turns = diariser._clean(
        {
            "messages": [
                {"role": "doctor", "message": "What brings you in?"},
                {"role": "patient", "message": "A headache."},
                {"role": "doctor", "message": "How long for?"},
            ]
        }
    )
    assert [turn["role"] for turn in turns] == ["doctor", "patient", "doctor"]
    assert turns[1]["message"] == "A headache."


def test_a_role_that_is_neither_is_dropped_rather_than_guessed() -> None:
    """Attributing a turn to the wrong speaker marks somebody else's words."""
    turns = diariser._clean(
        {
            "messages": [
                {"role": "Doctor", "message": "Hello."},
                {"role": "examiner", "message": "Two minutes remaining."},
                {"role": "patient", "message": "Hello."},
            ]
        }
    )
    assert [turn["role"] for turn in turns] == ["doctor", "patient"]


def test_empty_turns_are_dropped() -> None:
    turns = diariser._clean(
        {"messages": [{"role": "doctor", "message": "  "}, {"role": "patient", "message": "Yes."}]}
    )
    assert turns == [{"role": "patient", "message": "Yes."}]


@pytest.mark.parametrize(
    "parsed", [{"messages": "not a list"}, ["messages"], {"messages": [{"role": "narrator"}]}]
)
def test_a_shape_that_cannot_be_marked_is_refused(parsed: object) -> None:
    """Better no feedback than feedback built from a transcript nobody has."""
    with pytest.raises(TranscriptionFailed):
        diariser._clean(parsed)


async def test_an_empty_recording_never_reaches_the_model() -> None:
    with pytest.raises(TranscriptionFailed):
        await diariser.to_turns("   ")


def _settings(monkeypatch: pytest.MonkeyPatch, **keys: str) -> None:
    monkeypatch.setattr(diariser, "get_settings", lambda: Settings(**keys))


_CLAUDE_TURNS = '{"messages": [{"role": "patient", "message": "From Claude."}]}'
_OPENAI_TURNS = '{"messages": [{"role": "doctor", "message": "From OpenAI."}]}'


async def test_claude_splits_first_with_no_temperature_and_openai_is_not_asked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, anthropic_api_key="a", openai_api_key="o")
    providers = install_fake_sdks(monkeypatch, claude=_CLAUDE_TURNS, openai=_OPENAI_TURNS)

    turns = await diariser.to_turns("Hello.")

    sent = providers.claude_sent
    assert turns == [{"role": "patient", "message": "From Claude."}]
    assert providers.asked == ["claude"]
    assert sent["model"] == "claude-haiku-5-5"
    assert sent["messages"] == [{"role": "user", "content": "Hello."}]
    assert sent["output_config"]["effort"] == "low"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert not {"temperature", "tool_choice"} & set(sent)


async def test_openai_splits_when_claude_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch, anthropic_api_key="a", openai_api_key="o")
    providers = install_fake_sdks(monkeypatch, claude=RuntimeError("anthropic down"), openai=_OPENAI_TURNS)

    turns = await diariser.to_turns("Hello.")

    sent = providers.openai_sent
    assert turns == [{"role": "doctor", "message": "From OpenAI."}]
    assert sent["model"] == "gpt-6-luna"
    assert sent["reasoning_effort"] == "none"
    assert sent["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "turns", "schema": diariser.TURNS_SCHEMA, "strict": False},
    }
    assert sent["messages"][1] == {"role": "user", "content": "Hello."}
    assert "temperature" not in sent and "max_tokens" not in sent


async def test_openai_splits_when_the_anthropic_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch, openai_api_key="o")
    providers = install_fake_sdks(monkeypatch, openai=_OPENAI_TURNS)

    assert await diariser.to_turns("Hello.") == [{"role": "doctor", "message": "From OpenAI."}]
    assert providers.asked == ["openai"]


async def test_a_claude_reply_with_no_usable_turn_falls_back_to_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, anthropic_api_key="a", openai_api_key="o")
    providers = install_fake_sdks(
        monkeypatch, claude='{"messages": [{"role": "narrator", "message": "x"}]}', openai=_OPENAI_TURNS
    )

    assert await diariser.to_turns("Hello.") == [{"role": "doctor", "message": "From OpenAI."}]
    assert providers.asked == ["claude", "openai"]


async def test_no_key_at_all_is_a_transcription_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    with pytest.raises(TranscriptionFailed):
        await diariser.to_turns("Hello.")


async def test_claude_failing_with_no_openai_key_surfaces_claudes_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, anthropic_api_key="a")
    install_fake_sdks(monkeypatch, claude=RuntimeError("anthropic down"))

    with pytest.raises(TranscriptionFailed, match="anthropic down"):
        await diariser.to_turns("Hello.")
