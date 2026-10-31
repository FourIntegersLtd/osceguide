"""Recovering who said what from a single mixed recording.

A room-composite egress is one track: both voices, already mixed. Speaker
identity is not in the audio, so it is recovered afterwards from what was
said — a doctor asks the questions, a patient answers them. This is lossy,
knowingly so: per-participant egress would remove the guesswork at the cost
of two uploads to stitch.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.llm import CLAUDE_HAIKU, OPENAI_FAST, NoModelKey, claude_reply, first_that_answers, openai_reply
from app.core.ports import TranscriptionFailed
from app.core.settings import get_settings
from app.features.peer_practice.transcript_prompt import (
    HUMAN_TRANSCRIPT_CONVERSION_PROMPT,
    TURNS_SCHEMA,
)

_TIMEOUT_SECONDS = 180
# Claude's thinking counts in max_tokens, so a long consultation needs room beyond its turns.
_CLAUDE_MAX_TOKENS = 16_000
_OPENAI_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "turns", "schema": TURNS_SCHEMA, "strict": False},
}


async def to_turns(raw_transcript: str) -> list[dict[str, str]]:
    """Split raw speech into `doctor` / `patient` turns, in order.

    The roles are named for what `attempts` already understands: its worker
    treats `doctor` as the candidate, so nothing has to be translated between
    here and the marking. Claude splits first; OpenAI answers if Claude has no
    key or fails.
    """
    if not raw_transcript.strip():
        raise TranscriptionFailed("There is no transcript to split into turns")
    settings = get_settings()

    async def by_claude(api_key: str) -> list[dict[str, str]]:
        """The turns as Haiku splits them."""
        reply = await claude_reply(
            api_key,
            system=HUMAN_TRANSCRIPT_CONVERSION_PROMPT,
            messages=[{"role": "user", "content": raw_transcript}],
            max_tokens=_CLAUDE_MAX_TOKENS,
            timeout=_TIMEOUT_SECONDS,
            model=CLAUDE_HAIKU,
            schema=TURNS_SCHEMA,
            effort="low",
        )
        return _clean(json.loads(reply))

    async def by_openai(api_key: str) -> list[dict[str, str]]:
        """The turns as OpenAI splits them, asked when Claude has no key or failed."""
        reply = await openai_reply(
            api_key,
            system=HUMAN_TRANSCRIPT_CONVERSION_PROMPT,
            messages=[{"role": "user", "content": raw_transcript}],
            model=OPENAI_FAST,
            timeout=_TIMEOUT_SECONDS,
            # Reasoning off on purpose: this only cuts text where a speaker changes.
            reasoning_effort="none",
            response_format=_OPENAI_RESPONSE_FORMAT,
        )
        return _clean(json.loads(reply))

    try:
        return await first_that_answers(
            [
                ("claude", settings.anthropic_api_key, by_claude),
                ("openai", settings.openai_api_key, by_openai),
            ]
        )
    except NoModelKey as exc:
        raise TranscriptionFailed("No model key is configured, so turns cannot be recovered") from exc
    except TranscriptionFailed:
        raise
    except Exception as exc:  # noqa: BLE001 - every failure here is the same failure
        raise TranscriptionFailed(f"The transcript could not be split into turns: {exc}") from exc


def _clean(parsed: Any) -> list[dict[str, str]]:
    """Keep only the turns the model attributed to a doctor or a patient, with real text."""
    messages = parsed.get("messages") if isinstance(parsed, dict) else None
    if not isinstance(messages, list):
        raise TranscriptionFailed("The diarised transcript was not a list of turns")
    turns: list[dict[str, str]] = []
    for raw_turn in messages:
        if not isinstance(raw_turn, dict):
            continue
        role = str(raw_turn.get("role") or "").strip().lower()
        message = str(raw_turn.get("message") or "").strip()
        # An unknown role is dropped rather than guessed: a patient's words
        # attributed to the doctor would be marked as the doctor's.
        if role in {"doctor", "patient"} and message:
            turns.append({"role": role, "message": message})
    if not turns:
        raise TranscriptionFailed("No turns could be recovered from the transcript")
    return turns
