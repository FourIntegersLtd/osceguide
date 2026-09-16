"""The rendered prompt is byte-identical to what the engine produces.

The plan names this as an oracle and it is the most important one in the
attempts slice: the backend renders every prompt, the worker holds no
templates, and a candidate talks to whatever this produces. If it drifts, the
station a doctor practises is quietly not the station that was authored — and
nothing else in the suite would notice, because every other test asserts on
instructions it wrote itself.

Compared against `assessment-platform/tests/fixtures/prompts/*.txt`, the
engine's own golden files, rendered from the station fixtures beside them.
Skipped when the checkout is absent; the engine is installed by
`make engine-dev`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.features.attempts.renderer import build_renderer


def _find_checkout() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "assessment-platform"
        if (candidate / "packages" / "osce_assessment").is_dir():
            return candidate
    return None


_CHECKOUT = _find_checkout()
if _CHECKOUT is not None and str(_CHECKOUT / "packages") not in sys.path:
    sys.path.insert(0, str(_CHECKOUT / "packages"))

pytestmark = pytest.mark.skipif(_CHECKOUT is None, reason="assessment-platform checkout not present")


def _fixture(kind: str, name: str, suffix: str) -> Path:
    assert _CHECKOUT is not None
    return _CHECKOUT / "tests" / "fixtures" / kind / f"{name}{suffix}"


@pytest.mark.parametrize(
    ("name", "exam_code", "owner_kind"),
    [
        ("library_station_sca", "sca", "platform"),
        ("ortho_station_clinical", "ortho", "platform"),
        ("org_station_demo", "sca", "org"),
    ],
)
def test_the_backend_renders_exactly_what_the_engine_renders(
    name: str, exam_code: str, owner_kind: str
) -> None:
    station_file = _fixture("stations", name, ".json")
    prompt_file = _fixture("prompts", name, ".txt")
    if not station_file.exists() or not prompt_file.exists():
        pytest.skip(f"{name} has no golden pair in this checkout")

    content = json.loads(station_file.read_text(encoding="utf-8"))
    expected = prompt_file.read_text(encoding="utf-8")

    rendered = build_renderer().render(
        station={"owner_kind": owner_kind, "content": content},
        exam_code=exam_code,
        mode="patient",
    )

    assert str(rendered["instructions"]).strip() == expected.strip(), (
        f"{name}: the backend's render differs from the engine's golden file. "
        "The templates belong to the engine; nothing in platform-api may "
        "compose a prompt of its own."
    )


def test_a_station_with_no_patient_content_still_renders_something() -> None:
    """The engine substitutes a default rather than failing.

    Worth pinning: it is why `domain.scenario_is_renderable` has to detect the
    degradation *before* the render. Nothing about this output says it is a
    fallback.
    """
    rendered = build_renderer().render(
        station={"owner_kind": "platform", "content": {}}, exam_code="sca", mode="patient"
    )

    assert str(rendered["instructions"]).strip()
