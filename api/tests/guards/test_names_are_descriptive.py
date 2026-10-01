"""Every name in the app says what it holds, so a new engineer can read code without decoding it.

Single letters (loop and comprehension variables included), unexplained two-letter names and a short
list of placeholder words are refused. `_` (a value thrown away) and `T` (a type variable) are the only
single letters allowed. Class-level names are skipped: those are schema fields and table columns, which
are contracts named by the API and the database, not by the author of the code.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, is_route_handler, parse, python_files, rel

# Two-letter names that are words or standard abbreviations in this codebase.
TWO_LETTER_WORDS = {"id", "db", "tz", "s3", "ip", "at", "to", "by", "os", "re", "io", "uk", "gp", "cv"}
# Placeholder names that never say what the thing is.
PLACEHOLDERS = {
    "data", "obj", "tmp", "val", "res", "ret", "foo", "idx", "opts", "cfg", "cnt", "num", "fn", "cb", "el",
}  # fmt: skip


def vague_names(tree: ast.Module) -> list[tuple[int, str]]:
    """Every (line, name) that is a single letter, an unknown two-letter name or a placeholder.

    Class-level names and route handlers' parameters are skipped: the first are schema fields and table
    columns, the second are query and path parameters. Both are contracts, not the author's choice.
    """
    contracts = {
        id(target)
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        for statement in node.body
        if isinstance(statement, ast.AnnAssign | ast.Assign)
        for target in ast.walk(statement)
        if isinstance(target, ast.Name)
    } | {
        id(argument)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and is_route_handler(node)
        for argument in ast.walk(node.args)
        if isinstance(argument, ast.arg)
    }
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and id(node) not in contracts:
            name, line = node.id, node.lineno
        elif isinstance(node, ast.arg) and id(node) not in contracts:
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
    return sorted(found)


def test_there_is_code_to_scan() -> None:
    assert len(python_files(APP_ROOT)) >= 100


@pytest.mark.parametrize("path", python_files(APP_ROOT), ids=lambda path: rel(path))
def test_names_are_descriptive(path: Path) -> None:
    offenders = vague_names(parse(path))
    assert not offenders, (
        f"{rel(path)} has names that don't say what they hold: {offenders}. Name it for what it is "
        "(`for station in stations`, not `for s in stations`); see CONTRIBUTING.md, Naming."
    )


def test_the_guard_catches_a_loop_letter() -> None:
    tree = ast.parse("def total(prices):\n    return sum(p for p in prices)\n")
    assert vague_names(tree) == [(2, "p")]


def test_the_guard_leaves_contracts_alone() -> None:
    tree = ast.parse(
        'class Point:\n    x: int\n\n@router.get("/search")\nasync def search(q: str):\n    return q\n'
    )
    assert vague_names(tree) == []
