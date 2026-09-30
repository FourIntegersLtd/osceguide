"""What the worker must never know: prompts, station shapes, products, scoring."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "packages" / "livekit_assessment_worker"

FORBIDDEN_IMPORTS = ("osce_assessment.prompts", "osce_assessment.evaluation", "osce_assessment.schemas")
FORBIDDEN_WORDS = re.compile(r"\b(b2c|b2b|bmj|employer|org_slug|tenant_slug|app_type|station|firestore|supabase|exam)\b", re.IGNORECASE)


def test_importing_the_worker_loads_no_prompt_schema_or_evaluation_code() -> None:
    code = (
        "import sys\n"
        "import livekit_assessment_worker.session, livekit_assessment_worker.entrypoint\n"
        f"bad = [m for m in sys.modules if m.startswith({FORBIDDEN_IMPORTS!r})]\n"
        "print(sorted(bad))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=PACKAGE.parents[1], env={"PYTHONPATH": "packages", "PATH": ""})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "[]"


def test_worker_source_names_no_product_station_or_storage() -> None:
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text())
        docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                      if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                      and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
        for node in ast.walk(tree):
            if id(node) in docstrings:
                continue  # prose may explain what the worker avoids; code may not name it
            if isinstance(node, ast.Name) and FORBIDDEN_WORDS.search(node.id):
                offenders.append(f"{path.name}:{node.lineno} {node.id}")
            elif isinstance(node, ast.Attribute) and FORBIDDEN_WORDS.search(node.attr):
                offenders.append(f"{path.name}:{node.lineno} .{node.attr}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and FORBIDDEN_WORDS.search(node.value):
                offenders.append(f"{path.name}:{node.lineno} {node.value!r}")
    assert offenders == []
