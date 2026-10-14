"""No source file names an OpenAI model that retires on 2027-01-14.

OpenAI retires gpt-4o, gpt-4o-mini, gpt-4.1 and gpt-4.1-mini (and their dated
snapshots) on 2027-01-14; a default left on one of them breaks that day. The
audio models (`gpt-4o-transcribe`, `gpt-4o-mini-tts`, `gpt-4o-mini-transcribe`)
are not retiring, so only an exact model name, optionally dated, matches.

Only quoted string literals count (read through `ast`), so a comment or a
docstring that explains what a model replaced carries no penalty.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from tests.guards._scan import PROJECT_ROOT, docstring_nodes, parse, python_files

REPO_ROOT = PROJECT_ROOT.parent
RETIREMENT = "2027-01-14"
REPLACEMENT = "gpt-6-luna"
SCANNED_ROOTS = (
    REPO_ROOT / "api" / "app",
    REPO_ROOT / "assessment" / "packages",
)

RETIRED = re.compile(r"gpt-(?:4o(?:-mini)?|4\.1(?:-mini)?)(?:-\d{4}-\d{2}-\d{2})?")


def retired_literals(path: Path) -> list[tuple[int, str]]:
    """(line, literal) for each retired model name written as a string in code."""
    tree = parse(path)
    skipped = docstring_nodes(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skipped
        and RETIRED.fullmatch(node.value)
    ]


def test_there_is_code_to_scan() -> None:
    for root in SCANNED_ROOTS:
        assert python_files(root), f"{root} holds no Python files; the guard is looking in the wrong place"


def test_no_retired_model_is_named_in_source() -> None:
    hits = [
        f'{path.relative_to(REPO_ROOT)}:{line}  "{literal}" retires on {RETIREMENT}; use {REPLACEMENT}'
        for root in SCANNED_ROOTS
        for path in python_files(root)
        for line, literal in retired_literals(path)
    ]
    assert not hits, "Retired OpenAI model in source:\n" + "\n".join(hits)


def test_matcher_flags_retired_names_and_spares_audio_models(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        '"""Docstring about gpt-4o."""\n'
        "# gpt-4o in a comment\n"
        'a = "gpt-4o-2024-08-06"\n'
        'b = "gpt-4o-transcribe"\n'
        'c = "gpt-4o-mini-tts"\n'
        'd = "gpt-4o-mini-transcribe"\n'
        'e = "gpt-4.1-mini"\n'
        'f = "gpt-6-luna"\n'
    )
    assert retired_literals(sample) == [(3, "gpt-4o-2024-08-06"), (7, "gpt-4.1-mini")]
