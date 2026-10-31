"""Writes and parses the two-host podcast script (Ben and Michelle, UK GPs)."""

from __future__ import annotations

import re

from app.core.settings import Settings
from app.features.generation import service as generation
from app.features.media_production.slide_narration import complete

# At low effort a script takes about a minute and a half; a stall is cut off well before OpenAI is asked.
_CLAUDE_SECONDS = 150

SPEAKERS = ("Ben", "Michelle")

_SYSTEM_PROMPT = (
    "You write the script for a conversational medical-education podcast, "
    "hosted by Ben and Michelle, two UK GPs who are also close friends. "
    "You write only the dialogue, one line per turn, as `Ben: ...` or `Michelle: ...`."
)


def generate_script(settings: Settings, source_text: str) -> str:
    """Asks the model to turn `source_text` into a Ben-and-Michelle dialogue script.

    Tries `claude-sonnet-5-5` first, falling back to `gpt-6.1-sol` when Claude fails or has no key.
    """
    return complete(
        settings,
        generation.podcast_script_prompt(source_text),
        system=_SYSTEM_PROMPT,
        claude_first=True,
        claude_seconds=_CLAUDE_SECONDS,
    ).strip()


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
