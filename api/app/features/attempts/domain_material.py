"""One value out of a station document, read defensively.

Beside `domain_definition`, which answers "what does the worker get" for the
same document. What a candidate, a patient actor or an examiner gets is now
answered by the station's template audiences (`stations/domain_audience.py`,
called through `stations.service.audience_sections`); this module used to
carry the per-exam key lists that answered it before templates existed, which
moved there and to `stations/domain_content.py`'s legacy fallback once every
screen read by audience instead. What is left is the one primitive still
useful on its own: reading a block's value as text without tripping over
`None` or a value that was never a string.
"""

from __future__ import annotations

from typing import Any


def text(value: Any) -> str | None:
    """A block's value as trimmed text, or `None` if it holds nothing."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
