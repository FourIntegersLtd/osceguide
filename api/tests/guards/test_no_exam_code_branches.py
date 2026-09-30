"""Per-exam behaviour lives in `exams.settings`, never in a branch on an exam's code.

`if exam == "ortho"` is how the date label, the debrief modes, the station
subtypes and the generation prompts used to differ. Each such branch made an
institution's own exam behave like whichever exam the `else` happened to name,
and made a fifth exam a release rather than a row. The settings column
(`catalog.schemas.ExamSettings`) replaced them; this keeps them from growing back.

It fails on a comparison between a name ending in `exam` or `exam_code` and a
string literal (`==`, `!=`, `in`, `not in` against literal tuples, lists or
sets). `app/migration` is exempt: reading legacy records keyed by exam is its
job, and it is deleted once the last tenant is across.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.guards._scan import is_migration, parse, python_files, rel

_EXAM_NAME_SUFFIXES = ("exam", "exam_code")


def _names_an_exam(node: ast.expr) -> bool:
    """Whether this expression is a variable or attribute named like an exam code."""
    if isinstance(node, ast.Name):
        name = node.id
    elif isinstance(node, ast.Attribute):
        name = node.attr
    else:
        return False
    return name.lower().endswith(_EXAM_NAME_SUFFIXES)


def _is_string_literal(node: ast.expr) -> bool:
    """A string constant, or a tuple/list/set made only of string constants."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return bool(node.elts) and all(
            isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts
        )
    return False


def exam_code_branch_lines(path: Path) -> list[int]:
    """The line of every `exam == "literal"`-style comparison in one file."""
    lines: list[int] = []
    for node in ast.walk(parse(path)):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for position, operator in enumerate(node.ops):
            if not isinstance(operator, ast.Eq | ast.NotEq | ast.In | ast.NotIn):
                continue
            left, right = operands[position], operands[position + 1]
            if (_names_an_exam(left) and _is_string_literal(right)) or (
                _names_an_exam(right) and _is_string_literal(left)
            ):
                lines.append(node.lineno)
    return lines


def test_no_branch_on_an_exam_code() -> None:
    """No code in `app/` outside the legacy import branches on an exam code literal."""
    offenders = [
        f"{rel(path)}:{line}"
        for path in python_files()
        if not is_migration(path)
        for line in exam_code_branch_lines(path)
    ]
    assert offenders == [], (
        "Per-exam behaviour belongs in exams.settings (catalog.schemas.ExamSettings), "
        f"not a branch on the code: {offenders}"
    )


def test_the_guard_catches_a_branch(tmp_path: Path) -> None:
    """The scan finds the shapes it exists to refuse, and passes a settings read."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        'if exam == "ortho": pass\n'
        'if "casc" != self.exam_code: pass\n'
        'if exam_code in ("sca", "plab"): pass\n'
        "if settings.date_label == label: pass\n",
        encoding="utf-8",
    )
    assert exam_code_branch_lines(sample) == [1, 2, 3]
