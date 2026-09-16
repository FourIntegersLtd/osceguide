"""Shared AST helpers for the guards.

Scanning is limited to code (identifiers, attributes, keywords and runtime
string literals). Docstrings are excluded so prose that explains what a
module replaces carries no penalty.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
FEATURES_ROOT = APP_ROOT / "features"
CORE_ROOT = APP_ROOT / "core"


def python_files(root: Path = APP_ROOT) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def slice_dirs() -> list[Path]:
    """Feature slices only.

    `app/migration` lives outside `features/` precisely so it is not one: it has
    no routes, no domain and no place in the layer order, and it is deleted once
    every tenant is across.
    """
    if not FEATURES_ROOT.exists():
        return []
    return sorted(p for p in FEATURES_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_"))


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def docstring_nodes(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def code_tokens(path: Path) -> set[str]:
    """Every identifier and runtime string literal in a module, lowercased."""
    tree = parse(path)
    docstrings = docstring_nodes(tree)
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
        elif isinstance(node, ast.arg):
            tokens.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            tokens.add(node.name)
        elif isinstance(node, ast.keyword) and node.arg:
            tokens.add(node.arg)
        elif isinstance(node, ast.alias):
            tokens.add(node.name)
            if node.asname:
                tokens.add(node.asname)
        elif isinstance(node, ast.ImportFrom) and node.module:
            tokens.add(node.module)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            tokens.add(node.value)
    return {token.lower() for token in tokens}


def string_literals(path: Path) -> list[str]:
    """Runtime string literals (docstrings excluded), original case."""
    tree = parse(path)
    docstrings = docstring_nodes(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]


def imported_modules(path: Path) -> set[str]:
    """Fully qualified module names imported by a file (absolute imports only)."""
    tree = parse(path)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def attribute_names(path: Path) -> set[str]:
    tree = parse(path)
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


def offenders(tokens: Iterable[str], banned: Iterable[str]) -> list[str]:
    return sorted({b for b in banned for t in tokens if b in t})


def names_imported_from(path: Path, package: str) -> set[str]:
    """Names a module imports *from* a package, e.g. `select` in
    `from sqlalchemy import select`.

    Matching bare tokens instead catches `dict.update` and `dict.get`, which
    is how a guard earns a reputation for crying wolf and gets deleted.
    """
    tree = parse(path)
    found: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == package or node.module.startswith(f"{package}."))
        ):
            found.update(alias.asname or alias.name for alias in node.names)
    return found
