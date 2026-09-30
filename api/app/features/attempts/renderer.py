"""The engine adapter behind `core.ports.ProfileRenderer`.

The backend renders every prompt. The worker is handed finished instructions
and holds no templates, so anyone inventing a new station shape changes nothing
downstream.

One formatter renders every station, whoever authored it. What distinguishes one station's prompt
from another's is its template's **layout**: an ordered list of blocks, each with the role it plays,
which travels with the station.

The templates themselves belong to `osce_assessment`; this only hands the
station over and passes the text back. Imported lazily like `evaluator.py`, so
the API starts and the rest of the suite runs without the engine installed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.core.logging import get_logger
from app.core.ports import ProfileRenderer, RenderFailed

log = get_logger(__name__)


class EngineProfileRenderer:
    """Renders a station with `osce_assessment.prompts`."""

    def __init__(self, formatter: Any, examiner_context: Any, greetings: Mapping[str, Any]) -> None:
        self._formatter = formatter
        self._examiner_context = examiner_context
        self._greetings = greetings

    def render(
        self,
        *,
        station: dict[str, object],
        layout: Sequence[Mapping[str, Any]] | None = None,
        greeting: str | None = None,
        mode: str,
    ) -> dict[str, object]:
        """Turn a station's document into the instructions and greeting a worker is handed.

        Raises `RenderFailed` if the engine's formatter itself fails or produces no instructions;
        neither is served to a worker.
        """
        document = {
            "title": str(station.get("title") or ""),
            "content": station.get("content") if isinstance(station.get("content"), dict) else {},
        }
        persona = "examiner" if mode == "examiner" else "patient"

        try:
            instructions = self._formatter(document, layout, persona=persona)
            examiner_context = self._examiner_context(document, layout)
        except Exception as exc:  # noqa: BLE001 - any formatter failure is the same failure here
            raise RenderFailed(f"The station could not be rendered: {exc}") from exc

        text = str(instructions or "").strip()
        if not text:
            raise RenderFailed("The formatter produced no instructions.")

        return {
            "instructions": text,
            "greeting": greeting or self._greeting(mode),
            # What the marker is told and the candidate is not: the expected
            # answers a template marks `examiner`. Was the ortho formatter's
            # private business, so no other exam could have any.
            "examiner_context": examiner_context,
        }

    def _greeting(self, mode: str) -> str | None:
        """The opening line for this mode, if the engine defines one."""
        greeting = self._greetings.get(mode)
        return str(greeting) if greeting else None


def build_renderer() -> ProfileRenderer:
    """Wire the engine, or say plainly that it is not there."""
    try:
        from osce_assessment.prompts import (  # noqa: PLC0415
            EXAMINER_GREETINGS,
            PATIENT_GREETINGS,
            create_station_prompt,
            station_examiner_context,
        )
    except ImportError as exc:
        raise RenderFailed(
            "The osce_assessment engine is not installed, so no prompt can be rendered. "
            "Run `poetry install`; it comes from assessment/packages/osce_assessment "
            "in this repository."
        ) from exc

    return EngineProfileRenderer(
        create_station_prompt,
        station_examiner_context,
        {"patient": _first(PATIENT_GREETINGS), "examiner": _first(EXAMINER_GREETINGS)},
    )


def _first(greetings: object) -> str | None:
    """One sample greeting out of the engine's collection, whether it is a dict or a sequence."""
    if isinstance(greetings, dict):
        greetings = list(greetings.values())
    if isinstance(greetings, (list, tuple)) and greetings:
        return str(greetings[0])
    return None
