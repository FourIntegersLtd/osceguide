"""Every file, function and class in the app says in plain words what it is for.

A module needs a docstring (an empty `__init__.py` is fine). A function or class needs a docstring, or a
`#` comment directly above it. Route handlers, Pydantic models and enums use the `#` comment, because
their docstrings are published in openapi.json and would change the API document. Exempt: dunder
methods, classes in `schemas*.py`, and one-line functions whose name already says everything.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, python_files, rel

# Classes whose docstring reaches openapi.json, so they are commented with `#` and never required to
# have a docstring.
API_DOCUMENT_BASES = {"BaseModel", "RootModel", "Enum", "StrEnum", "IntEnum"}


def is_one_liner(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the body, ignoring a docstring, is one single-line statement."""
    body = [
        statement
        for statement in function.body
        if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant))
    ]
    return len(body) == 1 and body[0].end_lineno == body[0].lineno


def undocumented(source: str, file_name: str) -> list[str]:
    """Every part of one module that has neither a docstring nor a `#` comment directly above it."""
    tree = ast.parse(source)
    lines = source.splitlines()
    missing = [] if not source.strip() or ast.get_docstring(tree) else ["module docstring"]
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if node.name.startswith("__") or ast.get_docstring(node):
            continue
        if isinstance(node, ast.ClassDef):
            base_names = {getattr(base, "id", getattr(base, "attr", "")) for base in node.bases}
            if file_name.startswith("schemas") or base_names & API_DOCUMENT_BASES:
                continue
        elif is_one_liner(node):
            continue
        first_line = min([decorator.lineno for decorator in node.decorator_list] + [node.lineno])
        if first_line >= 2 and lines[first_line - 2].strip().startswith("#"):
            continue
        missing.append(f"{node.name} (line {node.lineno})")
    return missing


def test_there_is_code_to_scan() -> None:
    assert len(python_files(APP_ROOT)) >= 100


@pytest.mark.parametrize("path", python_files(APP_ROOT), ids=lambda path: rel(path))
def test_code_is_documented(path: Path) -> None:
    missing = undocumented(path.read_text(encoding="utf-8"), path.name)
    assert not missing, (
        f"{rel(path)} leaves {missing} unexplained. Say in one plain sentence what it does for the "
        "person using the product; see CONTRIBUTING.md, Comments."
    )


def test_the_guard_catches_a_bare_function() -> None:
    source = '"""Prices."""\n\ndef total(prices):\n    subtotal = sum(prices)\n    return subtotal\n'
    assert undocumented(source, "service.py") == ["total (line 3)"]


def test_the_guard_accepts_a_comment_above_a_route() -> None:
    source = (
        '"""Routes."""\n\n# List the plans on sale.\n@router.get("/plans")\n'
        "async def list_plans():\n    plans = []\n    return plans\n"
    )
    assert undocumented(source, "router.py") == []
