"""The shared worker infrastructure must not branch on which product it serves.

The legacy package took a ``product: "b2c" | "b2b"`` string and switched on
it. The port takes configuration. This scan keeps it that way.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import voice_infra

ROOT = Path(voice_infra.__file__).parent
BANNED = ("b2c", "b2b", "product", "org_slug", "tenant", "employer", "bmj")


def _code_tokens(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
        elif isinstance(node, ast.arg):
            tokens.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            tokens.add(node.name)
        elif isinstance(node, ast.keyword) and node.arg:
            tokens.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            tokens.add(node.value)
    return {t.lower() for t in tokens}


@pytest.mark.parametrize("path", sorted(ROOT.glob("*.py")), ids=lambda p: p.name)
def test_no_product_vocabulary_in_worker_infrastructure(path: Path) -> None:
    def mentions(banned: str, token: str) -> bool:
        return re.search(rf"(^|[^a-z0-9]){re.escape(banned)}([^a-z0-9]|$)", token) is not None

    offenders = sorted({b for b in BANNED for t in _code_tokens(path) if mentions(b, t)})
    assert not offenders, f"{path.name} uses {offenders}; take a BackendEndpoints value instead"
