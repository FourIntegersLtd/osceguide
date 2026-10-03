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

A comparison is not the only way to key behaviour by exam. A dict keyed by
exam codes, a `Literal["sca", "plab"]` type and an `exam_code or "sca"`
fallback all do the same thing without one. So a second check refuses any
catalogue exam code written as a string in the app at all. The files that
still do so are listed in `STILL_NAMES_AN_EXAM`, each with what has to move;
the list only shrinks.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from tests.guards._scan import PROJECT_ROOT, docstring_nodes, is_migration, parse, python_files, rel

_EXAM_NAME_SUFFIXES = ("exam", "exam_code")

# The codes of the exams the platform ships with, read from the seed so this
# guard names no exam itself.
CATALOGUE_EXAM_CODES = frozenset(
    str(exam["code"]).lower()
    for exam in json.loads((PROJECT_ROOT / "seeds" / "platform-starter.json").read_text(encoding="utf-8"))[
        "exams"
    ]
)

# Files that still write an exam code into code, and what has to move for each
# to come off this list. Nothing may be added: a new per-exam difference is a
# field on `ExamSettings`.
STILL_NAMES_AN_EXAM = {
    # The assistant's per-exam wording is Python keyed by exam code; it belongs with the exam's data.
    "app/features/assistant/content/packs/__init__.py",
    # A deck with no exam is rendered and stored as one particular exam's.
    "app/features/media_production/slide_av.py",
}


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


def exam_code_literal_lines(path: Path) -> list[int]:
    """The line of every catalogue exam code written as a string in one file, docstrings aside."""
    tree = parse(path)
    docstrings = docstring_nodes(tree)
    return sorted(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.lower() in CATALOGUE_EXAM_CODES
            and id(node) not in docstrings
        }
    )


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


def test_no_exam_code_is_written_into_the_app() -> None:
    """No file outside the legacy import and the known list names a catalogue exam in code."""
    offenders = [
        f"{rel(path)}:{lines}"
        for path in python_files()
        if not is_migration(path) and rel(path) not in STILL_NAMES_AN_EXAM
        if (lines := exam_code_literal_lines(path))
    ]
    assert offenders == [], (
        "An exam code written into code makes every other exam behave like that one. "
        f"Read the difference from exams.settings (core.exam_settings.ExamSettings) instead: {offenders}"
    )


def test_the_known_list_only_shrinks() -> None:
    """A file that no longer names an exam comes off the list, so it cannot quietly start again."""
    cleaned = sorted(name for name in STILL_NAMES_AN_EXAM if not exam_code_literal_lines(PROJECT_ROOT / name))
    assert cleaned == [], f"These no longer name an exam; remove them from STILL_NAMES_AN_EXAM: {cleaned}"


def test_the_guard_catches_an_exam_written_as_data(tmp_path: Path) -> None:
    """A dict key, a `Literal`, a default and a fallback are all found; a docstring is not."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        '"""How the sca exam is timed."""\n'
        'DURATIONS = {"sca": 720, "plab": 480}\n'
        'ExamCode = Literal["casc", "ortho"]\n'
        'def read(exam_code: str = "sca"): pass\n'
        'exam = exam_code or "SCA"\n'
        'label = "Exam date"\n',
        encoding="utf-8",
    )
    assert exam_code_literal_lines(sample) == [2, 3, 4, 5]


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
