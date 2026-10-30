"""No source names an AI model id that its provider shuts down within 240 days.

A hard-coded model id that a provider retires fails on the shutdown day with
nobody watching (gpt-4.1-nano, 2026-10-23, broke legacy transcript correction).
The table below is the one place that records provider shutdown dates; add a
row the day a provider announces a deprecation. A model in use fails here
from 240 days before its shutdown date, so the swap is planned, not urgent.

Rows stay until the id is gone from source. A file that only lists ids as data goes in
LISTS_NOT_USES with a reason. Use means a whole quoted string equal to an id, optionally with a provider
prefix ("google/gemini-3.1-flash-lite") or a dated snapshot suffix. Prose,
comments and substrings (`gpt-5` inside `gpt-5.4-mini`) do not count.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HORIZON = timedelta(days=240)

OPENAI = "https://developers.openai.com/api/docs/deprecations"
ANTHROPIC = "https://platform.claude.com/docs/en/about-claude/model-deprecations"
CARTESIA = "https://docs.cartesia.ai/build-with-cartesia/tts-models/api-changes"
LIVEKIT_INFERENCE = "LiveKit Inference model list"

# model id -> (shutdown date, replacement, source). Verified 2026-10-24.
RETIREMENTS: dict[str, tuple[str, str, str]] = {
    "gpt-4.1-nano": ("2026-10-23", "gpt-6-luna", OPENAI),
    "o3-mini": ("2026-10-23", "gpt-6-luna", OPENAI),
    "gpt-4o-2024-05-13": ("2026-10-23", "gpt-6-luna", OPENAI),
    "gpt-4o-realtime-preview": ("2026-05-07", "(see source)", OPENAI),
    "o3": ("2026-12-11", "gpt-6-luna", OPENAI),
    "gpt-5": ("2026-12-11", "gpt-6-luna", OPENAI),
    "gpt-5-mini": ("2026-12-11", "gpt-6-luna", OPENAI),
    "gpt-5-nano": ("2026-12-11", "gpt-6-luna", OPENAI),
    "tts-1": ("2027-01-06", "(see source)", OPENAI),
    "gpt-4o-mini-tts": ("2027-01-06", "(see source)", OPENAI),
    "gpt-4o": ("2027-01-14", "gpt-6-luna", OPENAI),
    "gpt-4o-mini": ("2027-01-14", "gpt-6-luna", OPENAI),
    "gpt-4.1-mini": ("2027-01-14", "gpt-6-luna", OPENAI),
    "gpt-4.1": ("2027-01-14", "gpt-6-luna", OPENAI),
    "gpt-4o-transcribe": ("2027-02-26", "(see source)", OPENAI),
    "gpt-5.4-nano": ("2027-04-01", "(see source)", OPENAI),
    "claude-sonnet-4-5": ("2026-11-30", "(see source)", ANTHROPIC),
    "sonic-2": ("2026-10-20", "(see source)", CARTESIA),
    "gemini-3.1-flash-lite": ("2027-05-07", "(see source)", LIVEKIT_INFERENCE),
}

SCANNED = (
    "api/app/",
    "api/scripts/",
    "assessment/packages/",
    "assessment/scripts/",
    "assessment/k8s/",
    "web/src/",
)
SUFFIXES = (".py", ".ts", ".tsx", ".mjs", ".js", ".yaml", ".yml", ".sh")
# Files that list ids as data (prices, lookups) rather than call a model with them.
LISTS_NOT_USES = {
    "assessment/scripts/model_bench.py": "PRICES table of candidate models for benchmarking",
    "assessment/packages/voice_infra/speech.py": "REASONING_MODEL_PREFIXES matches by prefix, calls no model",
}

_IDS = "|".join(re.escape(m) for m in sorted(RETIREMENTS, key=len, reverse=True))
QUOTED_ID = re.compile(rf"""(["'])(?:[a-z0-9-]+/)?(?P<id>{_IDS})(?:-\d{{4}}-\d{{2}}-\d{{2}})?\1""")


def due_models(text: str, today: date) -> list[tuple[int, str]]:
    """(line, id) for each quoted id whose shutdown is within the horizon of `today`."""
    return [
        (number, match["id"])
        for number, line in enumerate(text.splitlines(), 1)
        for match in QUOTED_ID.finditer(line)
        if date.fromisoformat(RETIREMENTS[match["id"]][0]) - today <= HORIZON
    ]


def tracked_sources() -> list[str]:
    git = shutil.which("git") or "git"
    out = subprocess.run(  # noqa: S603  fixed argv, no user input
        [git, "ls-files", *SCANNED], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [
        p
        for p in out
        if p.endswith(SUFFIXES) and "/build/" not in p and ".test." not in p and p not in LISTS_NOT_USES
    ]


def test_there_is_source_to_scan() -> None:
    files = tracked_sources()
    assert any(p.startswith("api/app/") for p in files) and any(p.startswith("web/src/") for p in files)
    assert all((REPO_ROOT / p).is_file() for p in LISTS_NOT_USES), (
        "allowlisted file moved; update LISTS_NOT_USES"
    )


def test_no_source_uses_a_model_near_its_shutdown() -> None:
    today = date.today()
    hits = []
    for path in tracked_sources():
        file = REPO_ROOT / path
        if not file.is_file():  # tracked but deleted in the working tree
            continue
        for line, model in due_models(file.read_text(errors="ignore"), today):
            shutdown, replacement, source = RETIREMENTS[model]
            hits.append(
                f'{path}:{line}  "{model}" shuts down {shutdown}; replacement: {replacement} ({source})'
            )
    assert not hits, (
        f"Model ids within {HORIZON.days} days of shutdown (table: tests/guards/test_model_retirements.py):\n"
        + "\n".join(hits)
    )


def test_matcher_flags_near_shutdown_ids_only_as_whole_quoted_ids() -> None:
    text = (
        'a = "gpt-5"\n'  # 1 flagged
        'b = "gpt-5.4-mini"\n'  # 2 different model, not in table
        "c = 'google/gemini-3.1-flash-lite'\n"  # 3 provider form, flagged
        'd = "gpt-4o-2024-08-06"\n'  # 4 dated snapshot of gpt-4o, flagged
        "# gpt-4o in a comment\n"  # 5 not quoted
        'e = "o3-mini"\n'  # 6 flagged as o3-mini, not o3
        'f = "gpt-4o-mini-transcribe"\n'  # 7 not in table
    )
    assert due_models(text, date(2026, 10, 24)) == [
        (1, "gpt-5"),
        (3, "gemini-3.1-flash-lite"),
        (4, "gpt-4o"),
        (6, "o3-mini"),
    ]
    assert due_models('a = "gpt-5.4-nano"\n', date(2026, 10, 24)) == [(1, "gpt-5.4-nano")]  # 159 days
    assert due_models('a = "gemini-3.1-flash-lite"\n', date(2026, 10, 24)) == [
        (1, "gemini-3.1-flash-lite")
    ]  # 195 days
    assert due_models('a = "gpt-5"\n', date(2026, 1, 1)) == []  # 344 days out: passes
