"""The tutor's instructions are byte-identical to what the engine produces.

The same oracle `test_prompt_rendering.py` is for the station prompt, and for
the same reason: the backend renders every prompt and the worker holds no
templates, so drift here means the tutor a doctor talks to is quietly not the
tutor that was written — and nothing else in the suite would notice, because
every other test asserts on instructions it wrote itself.

Compared against `assessment/tests/fixtures/prompts/dashboard_tutor.txt`,
rendered from the brief fixture beside it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.features.tutor_memory.renderer import LABELS, build_renderer


def _find_checkout() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "assessment"
        if (candidate / "packages" / "osce_assessment").is_dir():
            return candidate
    return None


_CHECKOUT = _find_checkout()
if _CHECKOUT is not None and str(_CHECKOUT / "packages") not in sys.path:
    sys.path.insert(0, str(_CHECKOUT / "packages"))

pytestmark = pytest.mark.skipif(_CHECKOUT is None, reason="assessment/ not present in this checkout")


def test_the_backend_renders_exactly_what_the_engine_renders() -> None:
    assert _CHECKOUT is not None
    brief_file = _CHECKOUT / "tests" / "fixtures" / "tutor" / "brief.json"
    prompt_file = _CHECKOUT / "tests" / "fixtures" / "prompts" / "dashboard_tutor.txt"
    if not brief_file.exists() or not prompt_file.exists():
        pytest.skip("no tutor golden pair in this checkout")

    brief = json.loads(brief_file.read_text(encoding="utf-8"))
    # The product's own labels, which is what the golden was rendered with —
    # and the point of the labels being the consumer's to supply.
    rendered = build_renderer().render(brief=brief, labels=LABELS)

    assert rendered.strip() == prompt_file.read_text(encoding="utf-8").strip()
