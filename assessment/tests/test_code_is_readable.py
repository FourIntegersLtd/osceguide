"""Every function and class says what it is for, and every name says what it holds.

A new engineer reads the engine and the workers without anyone beside them, so
a module, a class and a function each carry a docstring (or a `#` comment
directly above), and no name is a single letter or a placeholder such as
`data` or `tmp`. One-line functions and dunder methods are exempt from the
docstring rule; `_` and `T` are the only single letters allowed.

The code written before this rule is counted in `readability_debt.json`, one
number per file. A file may not go above its number, and when it drops the
number must be lowered with it, so the debt only ever shrinks. A file that is
not in the list owes nothing and must stay that way.

To lower a number after documenting a file, run:
    poetry run python tests/test_code_is_readable.py
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEBT_FILE = Path(__file__).with_name("readability_debt.json")
# The code that ships: the engine and workers, and how they are hosted.
SCANNED_ROOTS = ("packages", "hosting")

# Two-letter names that are words or standard abbreviations in this codebase.
TWO_LETTER_WORDS = {"id", "db", "tz", "ip", "at", "to", "by", "os", "re", "io", "uk", "gp", "ui"}
# Placeholder names that never say what the thing is.
PLACEHOLDERS = {"data", "obj", "tmp", "val", "res", "ret", "foo", "idx", "opts", "cfg", "cnt", "num", "fn", "cb", "el"}


def scanned_files() -> list[Path]:
    """Every Python file under the scanned roots, leaving out a locally built copy of the engine."""
    return sorted(
        path
        for root in SCANNED_ROOTS
        for path in (PROJECT_ROOT / root).rglob("*.py")
        if "__pycache__" not in path.parts and "build" not in path.parts
    )


def relative(path: Path) -> str:
    """The path as it is written in the debt file."""
    return str(path.relative_to(PROJECT_ROOT))


def is_one_liner(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the body, ignoring a docstring, is one single-line statement."""
    body = [
        statement
        for statement in function.body
        if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant))
    ]
    return len(body) == 1 and body[0].end_lineno == body[0].lineno


def undocumented(source: str) -> list[str]:
    """Every part of one module that has neither a docstring nor a `#` comment directly above it."""
    tree = ast.parse(source)
    lines = source.splitlines()
    missing = [] if not source.strip() or ast.get_docstring(tree) else ["module docstring"]
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if node.name.startswith("__") or ast.get_docstring(node):
            continue
        if not isinstance(node, ast.ClassDef) and is_one_liner(node):
            continue
        first_line = min([decorator.lineno for decorator in node.decorator_list] + [node.lineno])
        if first_line >= 2 and lines[first_line - 2].strip().startswith("#"):
            continue
        missing.append(f"{node.name} (line {node.lineno})")
    return missing


def vague_names(source: str) -> list[str]:
    """Every name that is a single letter, an unknown two-letter name or a placeholder.

    Names assigned directly in a class body are skipped: those are model fields,
    which are contracts with whoever sends the payload, not the author's choice.
    """
    tree = ast.parse(source)
    fields = {
        id(target)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for statement in node.body
        if isinstance(statement, ast.AnnAssign | ast.Assign)
        for target in ast.walk(statement)
        if isinstance(target, ast.Name)
    }
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and id(node) not in fields:
            name, line = node.id, node.lineno
        elif isinstance(node, ast.arg):
            name, line = node.arg, node.lineno
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            name, line = node.name, node.lineno
        else:
            continue
        if name in {"_", "T"} or name.startswith("__"):
            continue
        bare = name.lstrip("_")
        if len(bare) == 1 or bare in PLACEHOLDERS or (len(bare) == 2 and bare not in TWO_LETTER_WORDS):
            found.append((line, name))
    return [f"{name} (line {line})" for line, name in sorted(found)]


def problems(path: Path) -> list[str]:
    """Everything in one file that breaks either rule."""
    source = path.read_text(encoding="utf-8")
    return [f"no docstring: {item}" for item in undocumented(source)] + [
        f"vague name: {item}" for item in vague_names(source)
    ]


def recorded_debt() -> dict[str, int]:
    """How many problems each older file is still allowed, by path."""
    return json.loads(DEBT_FILE.read_text(encoding="utf-8"))


def test_there_is_code_to_scan() -> None:
    assert len(scanned_files()) >= 50


@pytest.mark.parametrize("path", scanned_files(), ids=relative)
def test_code_is_readable(path: Path) -> None:
    found = problems(path)
    allowed = recorded_debt().get(relative(path), 0)
    assert len(found) <= allowed, (
        f"{relative(path)} has {len(found)} unexplained parts or vague names and is allowed {allowed}. "
        f"Give each function and class one plain sentence, and name things for what they hold: {found}"
    )
    assert len(found) == allowed, (
        f"{relative(path)} is down to {len(found)} from {allowed}. Lower its number in "
        "tests/readability_debt.json (or run this file as a script) so it cannot creep back."
    )


def test_the_debt_file_lists_only_files_that_exist() -> None:
    known = {relative(path) for path in scanned_files()}
    assert sorted(set(recorded_debt()) - known) == []


def test_the_guard_catches_a_bare_function_and_a_loop_letter() -> None:
    source = '"""Prices."""\n\ndef total(prices):\n    subtotal = sum(p for p in prices)\n    return subtotal\n'
    assert undocumented(source) == ["total (line 3)"]
    assert vague_names(source) == ["p (line 4)"]


def test_the_guard_leaves_model_fields_alone() -> None:
    source = '"""Shapes."""\n\nclass Point:\n    """A place on the screen."""\n\n    x: int\n'
    assert undocumented(source) == []
    assert vague_names(source) == []


if __name__ == "__main__":
    # Rewrite the debt file from what the code looks like now.
    current = {relative(path): len(found) for path in scanned_files() if (found := problems(path))}
    DEBT_FILE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
