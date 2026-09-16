"""The engine adapter behind `core.ports.ProfileRenderer`.

The backend renders every prompt. The worker is handed finished instructions
and holds no templates, so an organisation inventing a new station shape
changes nothing downstream.

The templates themselves belong to `osce_assessment` — this only chooses the
right formatter for the station and hands back text. Nothing here composes a
prompt; if it ever needs to, the template belongs in the engine beside the
others, where the golden fixtures cover it.

Imported lazily like `evaluator.py`, so the API starts and the rest of the
suite runs without the engine installed.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.core.ports import ProfileRenderer, RenderFailed

log = get_logger(__name__)

# b2c's four products, and which engine formatter renders each. Ortho's
# stations are a different document shape with their own formatter; the other
# three share the consultation one.
_ORTHO = "ortho"


class EngineProfileRenderer:
    """Renders a station with `osce_assessment.prompts`."""

    def __init__(self, formatters: dict[str, Any]) -> None:
        self._formatters = formatters

    def render(self, *, station: dict[str, object], exam_code: str, mode: str) -> dict[str, object]:
        owner = str(station.get("owner_kind") or "platform")
        raw = station.get("content")
        content: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}

        try:
            if owner == "org":
                # An org authored its own shape; the template it supplied
                # renders it, which is why org stations do not go through the
                # library formatter.
                instructions = self._formatters["org"](content)
            elif exam_code.lower() == _ORTHO:
                instructions = self._formatters["ortho"](content)
            else:
                instructions = self._formatters["library"](content)
        except Exception as exc:  # noqa: BLE001 - any formatter failure is the same failure here
            raise RenderFailed(f"The station could not be rendered: {exc}") from exc

        text = str(instructions or "").strip()
        if not text:
            raise RenderFailed("The formatter produced no instructions.")

        return {"instructions": text, "greeting": self._greeting(mode)}

    def _greeting(self, mode: str) -> str | None:
        greetings = self._formatters.get("greetings") or {}
        value = greetings.get(mode)
        return str(value) if value else None


def build_renderer() -> ProfileRenderer:
    """Wire the engine, or say plainly that it is not there."""
    try:
        from osce_assessment.prompts import (  # noqa: PLC0415
            PATIENT_GREETINGS,
            ConversationPromptFormatter,
            OrthoPromptFormatter,
            create_org_station_prompt,
        )
    except ImportError as exc:
        raise RenderFailed(
            "The osce_assessment engine is not installed, so no prompt can be rendered. "
            "Run `make engine-dev` locally, or pin the `engine-vX.Y.Z` tag in "
            "pyproject.toml for a deployment."
        ) from exc

    return EngineProfileRenderer(
        {
            "library": ConversationPromptFormatter.create_prompt,
            "ortho": OrthoPromptFormatter.create_ortho_prompt,
            "org": create_org_station_prompt,
            "greetings": {"patient": _first(PATIENT_GREETINGS)},
        }
    )


def _first(greetings: object) -> str | None:
    if isinstance(greetings, dict):
        greetings = list(greetings.values())
    if isinstance(greetings, (list, tuple)) and greetings:
        return str(greetings[0])
    return None
