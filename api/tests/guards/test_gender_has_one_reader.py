"""A station's patient gender is read by one rule, `osce_assessment.contracts.parse_gender`.

A hand-written `("m", "male")` set once sent "Male, 45" to the worker as unknown, and every such
patient spoke with a female voice. The worker, platform-api and the engine must agree, so no
attempts module spells the gender words out; it calls the parser.
"""

from __future__ import annotations

import ast

from tests.guards._scan import FEATURES_ROOT, rel

SPELLINGS = {"m", "male", "f", "female", "man", "woman"}


def test_attempts_code_spells_no_gender_word() -> None:
    offenders = [
        f"{rel(path)}:{node.lineno} {node.value!r}"
        for path in (FEATURES_ROOT / "attempts").glob("*.py")
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.lower() in SPELLINGS
    ]
    assert offenders == [], f"use osce_assessment.contracts.parse_gender: {offenders}"
