"""Writes and parses the two-host podcast script (Ben and Michelle, UK GPs)."""

from __future__ import annotations

import logging
import re

from app.core.settings import Settings
from app.features.generation import service as generation

PODCAST_SCRIPT_MODEL = "o3"
PODCAST_SCRIPT_FALLBACK_MODEL = "claude-sonnet-4-5"

logger = logging.getLogger(__name__)

SPEAKERS = ("Ben", "Michelle")

_SYSTEM_PROMPT = (
    "You write the script for a conversational medical-education podcast, "
    "hosted by Ben and Michelle, two UK GPs who are also close friends. "
    "You write only the dialogue, one line per turn, as `Ben: ...` or `Michelle: ...`."
)


def generate_script(settings: Settings, source_text: str) -> str:
    """Asks the model to turn `source_text` into a Ben-and-Michelle dialogue script.

    Tries `o3` first, falling back to `claude-sonnet-4-5` when the primary fails.
    """
    prompt = generation.podcast_script_prompt(source_text)
    if settings.openai_api_key.strip():
        from openai import OpenAI  # optional dependency

        client = OpenAI(api_key=settings.openai_api_key)
        try:
            response = client.chat.completions.create(
                model=PODCAST_SCRIPT_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            logger.warning(
                "Podcast script generation via %s failed, falling back to %s",
                PODCAST_SCRIPT_MODEL,
                PODCAST_SCRIPT_FALLBACK_MODEL,
                exc_info=True,
            )

    from anthropic import Anthropic  # optional dependency

    fallback_client = Anthropic(api_key=settings.anthropic_api_key)
    fallback_response = fallback_client.messages.create(
        model=PODCAST_SCRIPT_FALLBACK_MODEL,
        max_tokens=8000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return next((block.text for block in fallback_response.content if block.type == "text"), "").strip()


def split_script(script: str) -> list[tuple[str, str]]:
    """Breaks a `Ben: ...` / `Michelle: ...` script into (speaker, line) pairs, one per turn."""
    text = re.sub(
        r"(?im)^\s*\**(ben|michelle)\**\s*:\**", lambda match: f"\n{match.group(1).capitalize()}:", script
    )
    parts = re.split(r"\n+(Ben|Michelle):[ \t]*", "\n" + text)
    turns: list[tuple[str, str]] = []
    for index in range(1, len(parts) - 1, 2):
        line = re.sub(r'["“”]', "", " ".join(parts[index + 1].split())).strip()
        if line:
            turns.append((parts[index], line))
    return turns
