"""The two things every PDF the api hands out needs: a Unicode face and quiet output.

The face is the bundled DejaVu file, not a system font: a name outside Latin-1
has to render on a Railway host that has none. CJK and emoji, which DejaVu lacks,
fall back to two bundled single-weight subsets (Noto Sans SC, Noto Emoji; OFL,
licences beside them). Used by a released result and by a person's own data export.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fpdf import FPDF

FACE = "DejaVuSans"
_FONTS = Path(__file__).resolve().parent / "fonts"
_FACE_FILE = _FONTS / "DejaVuSans.ttf"
_FALLBACKS = {"NotoSansSC": "NotoSansSC-Subset.ttf", "NotoEmoji": "NotoEmoji-Regular.ttf"}


def add_face(document: FPDF) -> None:
    """Register the bundled Unicode face on `document` under `FACE`, with the CJK and
    emoji faces behind it for any glyph it lacks."""
    document.add_font(FACE, "", str(_FACE_FILE))
    for name, file in _FALLBACKS.items():
        document.add_font(name, "", str(_FONTS / file))
    document.set_fallback_fonts(list(_FALLBACKS))


def output_bytes(document: FPDF) -> bytes:
    """The finished file. Subsetting the face logs one line per table; a download
    is not an operational event, so those lines stay off the request log."""
    subset_log = logging.getLogger("fontTools")
    previous_level = subset_log.level
    subset_log.setLevel(logging.WARNING)
    try:
        produced = document.output()
    finally:
        subset_log.setLevel(previous_level)
    return bytes(produced)
