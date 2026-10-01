"""The engine adapter behind `core.ports.TutorPromptRenderer`.

The backend renders every prompt; the worker holds no templates and is handed
finished text. Imported lazily, like `attempts/renderer.py`, so the API starts
and the rest of the suite runs without the engine installed.

The labels are this product's words for its own material. They are passed in
rather than written in the engine, which is what keeps a prompt template free
of any product's vocabulary.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.logging import get_logger
from app.core.ports import RenderFailed, TutorPromptRenderer

log = get_logger(__name__)

# The names a doctor sees on their own screen, so the tutor says "have a look
# at A to Z" rather than describing a section they would have to go and find.
# Carried over from the consumer app deliberately: changing what these are
# called is a product decision, not a prompt one.
LABELS = {"summaries": "A to Z", "slides": "Slides", "stations": "AI Practice"}


class EngineTutorPromptRenderer:
    """Renders a learner's brief with `osce_assessment.prompts`."""

    def __init__(self, formatter: Any) -> None:
        self._formatter = formatter

    def render(self, *, brief: dict[str, object], labels: Mapping[str, str]) -> str:
        """Turn one learner's brief into the finished system prompt the worker is handed."""
        try:
            instructions = self._formatter(brief, labels=dict(labels))
        except Exception as exc:  # noqa: BLE001 - any formatter failure is the same failure here
            raise RenderFailed(f"The tutor brief could not be rendered: {exc}") from exc
        text = str(instructions or "").strip()
        if not text:
            raise RenderFailed("The formatter produced no instructions.")
        return text


def build_renderer() -> TutorPromptRenderer:
    """Wire the engine, or say plainly that it is not there."""
    try:
        from osce_assessment.prompts import DashboardTutorFormatter
    except ImportError as exc:
        raise RenderFailed(
            "The osce_assessment engine is not installed, so no tutor prompt can be rendered. "
            "Run `poetry install`; it comes from assessment/packages/osce_assessment "
            "in this repository."
        ) from exc

    return EngineTutorPromptRenderer(DashboardTutorFormatter.create_prompt)
