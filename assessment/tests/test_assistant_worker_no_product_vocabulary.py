"""The assistant worker names no product, exam, client or persona anywhere in code.

``test_assistant_worker_modes`` guards session-type strings but exempts the
``ui_guidance`` and ``prompts`` subtrees; this scan covers the whole package.
Content, labels and personas arrive rendered from the dispatching backend.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import livekit_assistant_worker

ROOT = Path(livekit_assistant_worker.__file__).parent
BANNED = ("sca", "plab", "casc", "ortho", "b2c", "b2b", "bmj", "employer", "tenant", "org_slug",
          "marketplace", "ai practice", "osce guide", "athena")


def _code_tokens(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
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
        elif isinstance(node, ast.alias):
            tokens.add(node.asname or node.name)
        elif isinstance(node, ast.keyword) and node.arg:
            tokens.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            tokens.add(node.value)
    return {t.lower() for t in tokens}


def _mentions(banned: str, token: str) -> bool:
    return re.search(rf"(^|[^a-z0-9]){re.escape(banned)}([^a-z0-9]|$)", token) is not None


@pytest.mark.parametrize("path", sorted(ROOT.rglob("*.py")), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_product_vocabulary_in_assistant_worker(path: Path) -> None:
    offenders = sorted({b for b in BANNED for t in _code_tokens(path) if _mentions(b, t)})
    assert not offenders, f"{path.relative_to(ROOT)} uses {offenders}; the backend renders content, the worker stays agnostic"


def test_scan_would_catch_a_leak(tmp_path: Path) -> None:
    leak = tmp_path / "leak.py"
    leak.write_text('LABEL = "Open Marketplace"\n')
    assert any(_mentions("marketplace", t) for t in _code_tokens(leak))
