"""Old bucket paths and where each file now lives, applied to every link that enters the database.

The platform has a bucket of its own (`core.bucket_layout.BUCKET`, private). The legacy site stored links
to files in the old bucket, in author-named folders (`yahayakenny/`, `fourint/`, `Four Integers Ltd/`), in
generation folders (`teaching_videos/v2/`, `podcasts/v4/`) and in a few plain ones (`avatars/`,
`human_practice/`). Each of those files is copied to `<kind>/<exam>/...` in the new bucket. Two things
say where:
- `bucket_moves.json` (next to this file) lists the files that change name or exam folder, one by one;
- `PREFIX_MOVES` lists whole folders that move unchanged.
`platform_key` answers for any key; `rewrite_links` does the same for links inside text.

Two callers use it, so a moved link can never come back:
- the legacy importers (`b2c_firestore`, the station and study-material exports) rewrite each document as
  they read it, so the nightly sync cannot copy an old link over a rewritten one;
- `scripts/move_bucket_links.py` rewrites the rows already in the database.

Only a link on the old bucket's host is rewritten, to the new bucket's host and the file's new path, and a
link keeps the spelling its path had (plain, `%20`, `+` or fully encoded). Links that name no moved file,
and links on any other host, come back exactly as they were.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus

from app.core import bucket_layout

MOVES_FILE = Path(__file__).with_name("bucket_moves.json")
BUCKET_HOST_MARK = "amazonaws.com"
NEW_HOST = f"https://{bucket_layout.BUCKET}.s3.{bucket_layout.REGION}.amazonaws.com"

# Every spelling of the old bucket's address (virtual-host and path style, regional and global).
_LEGACY = re.escape(bucket_layout.LEGACY_BUCKET)
LEGACY_HOST = (
    rf"https?://(?:{_LEGACY}\.s3[a-z0-9.-]*\.amazonaws\.com|s3[a-z0-9.-]*\.amazonaws\.com/{_LEGACY})"
)

# Whole folders that move as they are: old folder, new folder. Practice recordings were `human_practice/`
# in the legacy site and `peer_practice/` in the first platform writer; both land in one folder.
PREFIX_MOVES: tuple[tuple[str, str], ...] = (
    ("human_practice/", bucket_layout.PEER_PRACTICE),
    ("peer_practice/", bucket_layout.PEER_PRACTICE),
    ("avatars/", bucket_layout.AVATARS),
    ("stations/", bucket_layout.STATIONS),
    ("marketing/", bucket_layout.MARKETING),
    ("archive/", bucket_layout.ARCHIVE),
)


def load_moves() -> dict[str, str]:
    """Every old key mapped to its new key, as listed in `bucket_moves.json`."""
    return json.loads(MOVES_FILE.read_text())


def old_to_new_paths(moves: dict[str, str]) -> list[tuple[str, str]]:
    """Every `/old/key` path a stored link may carry, with its `/new/key` replacement.

    A key with spaces or accents is stored raw, with its spaces encoded (`%20` or `+`) or fully encoded. Each
    spelling of the old key is paired with the same spelling of the new one. Longest first, so a key
    that is the start of another is never cut short.
    """
    spellings = (
        lambda key: key,
        lambda key: key.replace(" ", "%20"),  # only the spaces encoded, the way a browser writes a link
        lambda key: key.replace(" ", "+"),
        lambda key: quote(key, safe="/"),  # everything encoded, the way a library writes one
        lambda key: quote_plus(key, safe="/"),
    )
    pairs: dict[str, str] = {}
    for old, new in moves.items():
        for spell in spellings:
            pairs[f"/{spell(old)}"] = f"/{spell(new)}"
    return sorted(pairs.items(), key=lambda pair: len(pair[0]), reverse=True)


def platform_key(key: str, moves: dict[str, str] | None = None) -> str | None:
    """Where the file at `key` in the old bucket belongs in the new one, or None when it is not ours to move.

    A file nothing in the app uses has no destination.
    """
    listed = load_moves() if moves is None else moves
    if key in listed:
        return listed[key]
    for old_folder, new_folder in PREFIX_MOVES:
        if key.startswith(old_folder):
            return new_folder + key[len(old_folder) :]
    return None


def _folder_pattern() -> re.Pattern[str]:
    """Links on the old bucket into one of `PREFIX_MOVES`' folders.

    Tied to the old bucket's own host so another bucket's `avatars/` folder, or an app route that happens to
    contain `/stations/`, is never touched.
    """
    folders = "|".join(re.escape(old) for old, _new in PREFIX_MOVES)
    return re.compile(rf"{LEGACY_HOST}/(?P<folder>{folders})")


def _listed_pattern(pairs: list[tuple[str, str]]) -> tuple[re.Pattern[str], dict[str, str]]:
    """One pattern that finds any listed old path on the old bucket, and the lookup to its new path."""
    return re.compile(
        LEGACY_HOST + "(?P<path>" + "|".join(re.escape(old) for old, _new in pairs) + ")"
    ), dict(pairs)


@lru_cache(maxsize=1)
def _matcher() -> tuple[re.Pattern[str], dict[str, str]]:
    """The pattern and lookup for the bundled list."""
    return _listed_pattern(old_to_new_paths(load_moves()))


def rewrite_links(document_text: str, moves: dict[str, str] | None = None) -> str:
    """The text with every old-bucket link swapped for its place in the new bucket.

    Uses the bundled list unless `moves` is given. Folder moves apply only with the bundled list.
    """
    if BUCKET_HOST_MARK not in document_text:
        return document_text
    pattern, lookup = _matcher() if moves is None else _listed_pattern(old_to_new_paths(moves))
    document_text = pattern.sub(lambda match: NEW_HOST + lookup[match.group("path")], document_text)
    if moves is not None:
        return document_text
    new_folder_of = dict(PREFIX_MOVES)
    return _folder_pattern().sub(
        lambda match: f"{NEW_HOST}/{new_folder_of[match.group('folder')]}", document_text
    )


def rewrite_value(value: Any) -> Any:
    """A copy of a document (any nesting of dicts, lists and strings) with every moved link rewritten."""
    if isinstance(value, str):
        return rewrite_links(value)
    if isinstance(value, dict):
        return {key: rewrite_value(nested_value) for key, nested_value in value.items()}
    if isinstance(value, list):
        return [rewrite_value(nested_value) for nested_value in value]
    return value
