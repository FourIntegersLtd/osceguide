"""Every tracked source file has exactly one owner in `.claude/OWNERS.md`.

A file with no owner is a file no agent reads the area notes for; a file with
two owners is one two agents will edit at once. Both fail here, so adding a
file in a new place forces the table to say who owns it.

Row format in OWNERS.md: ``| `glob`, `glob`, `!excluded-glob` | owner |``.
`*` matches within one path segment, `**` across segments, `{a,b}` is
expanded, and a `!` glob removes files from the row.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OWNERS_FILE = REPO_ROOT / ".claude" / "OWNERS.md"

GIT = shutil.which("git") or "git"
APPS = ("api/", "web/", "assessment/")
SOURCE_SUFFIXES = (".py", ".ts", ".tsx", ".mjs", ".js", ".sql", ".sh")
GENERATED = ("web/src/foundation/platform-client/schema.d.ts",)
SKIPPED_PARTS = ("node_modules", "__pycache__")

ROW = re.compile(r"^\|\s*(?P<globs>`[^|]+?)\s*\|\s*(?P<owner>[a-z-]+-owner)\s*\|\s*$")
BRACES = re.compile(r"\{([^{}]*)\}")


def _expand(glob: str) -> list[str]:
    match = BRACES.search(glob)
    if match is None:
        return [glob]
    out: list[str] = []
    for option in match.group(1).split(","):
        out.extend(_expand(glob[: match.start()] + option + glob[match.end() :]))
    return out


def _regex(glob: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif glob.startswith("**", i):
            out += ".*"
            i += 2
        elif glob[i] == "*":
            out += "[^/]*"
            i += 1
        elif glob[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(glob[i])
            i += 1
    return re.compile(out + r"\Z")


class Row:
    def __init__(self, owner: str, globs: list[str]) -> None:
        self.owner = owner
        self.text = ", ".join(globs)
        self.include = [_regex(e) for g in globs if not g.startswith("!") for e in _expand(g)]
        self.exclude = [_regex(e) for g in globs if g.startswith("!") for e in _expand(g[1:])]

    def matches(self, path: str) -> bool:
        return any(p.match(path) for p in self.include) and not any(p.match(path) for p in self.exclude)


def _split_globs(cell: str) -> list[str]:
    """Split on commas that are not inside braces."""
    parts: list[str] = []
    depth = 0
    current = ""
    for char in cell:
        depth += (char == "{") - (char == "}")
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    return [p.strip().strip("`") for p in [*parts, current] if p.strip()]


def parse_rows(text: str) -> list[Row]:
    rows: list[Row] = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match:
            rows.append(Row(match["owner"], _split_globs(match["globs"])))
    return rows


def tracked_source_files() -> list[str]:
    """Tracked files plus new ones not yet added, so a new file without an owner fails here
    before it is committed, not first in CI."""
    listing = subprocess.run(  # noqa: S603 - fixed argv, no user input
        [GIT, "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return [
        path
        for path in listing
        if path.startswith(APPS)
        and path.endswith(SOURCE_SUFFIXES)
        and path not in GENERATED
        and not any(part in path.split("/") for part in SKIPPED_PARTS)
    ]


def owners_per_file(paths: list[str], rows: list[Row]) -> dict[str, list[str]]:
    return {path: [row.text for row in rows if row.matches(path)] for path in paths}


def test_row_exclude_glob_removes_a_path() -> None:
    row = Row("x", ["web/src/**", "!web/src/domains/assess/**"])
    assert row.matches("web/src/foundation/a.ts")
    assert not row.matches("web/src/domains/assess/a.ts")


def test_row_brace_expansion_matches_each_alternative() -> None:
    row = Row("x", ["web/src/{foundation,surfaces}/**"])
    assert row.matches("web/src/foundation/a.ts")
    assert row.matches("web/src/surfaces/a.ts")
    assert not row.matches("web/src/domains/a.ts")


def test_every_source_file_has_exactly_one_owner() -> None:
    rows = parse_rows(OWNERS_FILE.read_text())
    claims = owners_per_file(tracked_source_files(), rows)
    unowned = sorted(p for p, hit in claims.items() if not hit)
    shared = sorted(f"{p}: {hit}" for p, hit in claims.items() if len(hit) > 1)
    assert not unowned, f"{len(unowned)} files match no row in .claude/OWNERS.md: {unowned[:25]}"
    assert not shared, f"{len(shared)} files match two rows in .claude/OWNERS.md: {shared[:25]}"


def test_a_file_in_no_row_is_reported() -> None:
    rows = parse_rows(OWNERS_FILE.read_text())
    claims = owners_per_file(["api/app/features/not_a_slice/router.py"], rows)
    assert claims == {"api/app/features/not_a_slice/router.py": []}


def test_every_row_owner_has_an_agent_file() -> None:
    owners = {row.owner for row in parse_rows(OWNERS_FILE.read_text())}
    agents = {p.stem for p in (REPO_ROOT / ".claude" / "agents").glob("*-owner.md")}
    assert owners == agents
