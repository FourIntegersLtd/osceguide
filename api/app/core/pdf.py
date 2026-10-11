"""The two things every PDF the api hands out needs: a Unicode face and quiet output.

The face is the bundled DejaVu file, not a system font: a name outside Latin-1
has to render on a Railway host that has none. Used by a released result and
by a person's own data export.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fpdf import FPDF

FACE = "DejaVuSans"
_FACE_FILE = Path(__file__).resolve().parent / "fonts" / "DejaVuSans.ttf"


def add_face(document: FPDF) -> None:
    """Register the bundled Unicode face on `document` under `FACE`."""
    document.add_font(FACE, "", str(_FACE_FILE))


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
