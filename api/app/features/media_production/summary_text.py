from __future__ import annotations

from typing import Any


def _lines(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(value) for value in items if value is not None and str(value).strip()]


def format_summary_for_podcast(title: str, content: dict[str, Any]) -> str:

    def block(heading: str, items: list[str]) -> str:
        body = "\n".join(f"  - {line}" for line in items) if items else "  None provided"
        return f"\n{heading}\n{body}"

    name = title.strip() or str(content.get("name") or "Summary")
    return (
        f"Medical Condition Summary: {name}"
        + block("Red Flags and Warning Signs:", _lines(content.get("red_flags")))
        + block("Key Examinations and Investigations:", _lines(content.get("examinations")))
        + block("Clinical Management and Treatment:", _lines(content.get("brief_management")))
        + block("Psychosocial Considerations:", _lines(content.get("psychosocial_aspects")))
    ).strip()
