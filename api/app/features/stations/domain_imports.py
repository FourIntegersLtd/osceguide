"""Rules for importing a station from an uploaded document. Pure: no storage, no model.

The cheap checks run before anything is parsed or any model is called, so a
file that was never going to be a station costs nothing to refuse. The checks on
the drafted station run after the model has answered, and are what lets an
author trust that the draft says what their document said.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import StrEnum
from typing import Any

from app.core.document_text import DOCX_SUFFIX, PDF_SUFFIX

# Ten megabytes is far more than a station document with text weighs and stops
# a large upload from being parsed in the request that took it.
MAX_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = (PDF_SUFFIX, DOCX_SUFFIX)
# Fewer characters than this and there was nothing to read: a scan with no text
# layer, or a file that is not a station. Refused rather than sent to a model
# to invent a station from.
MIN_TEXT_CHARS = 200
# One station, not a whole library in one file. Past this the model would have
# to drop text to answer, and a draft that silently lost a page is worse than a
# refusal that says to split the file.
MAX_TEXT_CHARS = 120_000
# The widest title `CreateStation` accepts.
MAX_TITLE_CHARS = 300
# The widest filename the row stores.
MAX_FILENAME_CHARS = 255
# How many of an owner's imports the list shows, newest first.
RECENT_LIMIT = 50


class ImportStatus(StrEnum):
    DRAFTING_TEMPLATE = "drafting_template"
    TEMPLATE_READY = "template_ready"
    DRAFTING_STATION = "drafting_station"
    COMPLETED = "completed"
    FAILED = "failed"


class InvalidImport(Exception):
    """A file that cannot be imported as a station. Mapped to `invalid_import_file`."""


def validate_upload(*, filename: str, size: int) -> None:
    """Refuse a file that cannot be a station document, before any work is done on it."""
    if not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise InvalidImport("Only PDF and Word (.docx) files can be imported.")
    if size > MAX_BYTES:
        raise InvalidImport(f"File too large. Maximum size is {MAX_BYTES // (1024 * 1024)}MB.")
    if size == 0:
        raise InvalidImport("That file is empty.")


def ensure_usable_text(text: str) -> str:
    """The extracted text, or a refusal when the document held too little or too much to import."""
    cleaned = (text or "").strip()
    if len(cleaned) < MIN_TEXT_CHARS:
        raise InvalidImport(
            "That file contains too little text to import. A scanned document has to be "
            "exported as text first."
        )
    if len(cleaned) > MAX_TEXT_CHARS:
        raise InvalidImport("That file is too long to import as one station. Upload one station per file.")
    return cleaned


def may_draft_station(status: str, *, has_template: bool) -> bool:
    """Whether a station may be drafted from an import now.

    It needs a template, and must not already be drafting or done. A failed
    import that has a template may be tried again: the template survived, and
    the failure was the station step.
    """
    if not has_template:
        return False
    return status in (ImportStatus.TEMPLATE_READY.value, ImportStatus.FAILED.value)


def is_empty(value: Any) -> bool:
    """Whether a block's value holds nothing: the document had nothing for it."""
    return value in (None, "", [], {})


def station_title(drafted_title: str, filename: str) -> str:
    """The draft station's title: the document's own, or the file's name when it gave none."""
    title = drafted_title.strip() or filename.rsplit(".", 1)[0].strip() or "Imported station"
    return title[:MAX_TITLE_CHARS]


def empty_block_ids(block_ids: Sequence[str], content: dict[str, Any]) -> list[str]:
    """The template's blocks the drafted station has nothing in, in template order."""
    return [block_id for block_id in block_ids if is_empty(content.get(block_id))]


def reworded_block_ids(content: dict[str, Any], source_text: str) -> list[str]:
    """Blocks holding text that is not in the source document word for word.

    An import copies; it does not write. Comparing ignores case, line breaks,
    table separators and the style of quotes and dashes, which a PDF and a model
    both change freely, so what is left is a real difference in wording. Every
    cell of a table and every item of a grouped list is compared on its own. A
    block named here is not refused: it is shown to the author to check.
    """
    source = _comparable(source_text)
    return [
        block_id
        for block_id, value in content.items()
        if any(_comparable(passage) not in source for passage in _passages(value))
    ]


def _passages(value: Any) -> list[str]:
    """Every piece of text in a block's value: a string, list items, table cells, grouped items.

    The keys of a table row or a grouped list are the template's and the
    document's headings, not copied text, so they are not compared.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [passage for item in value for passage in _passages(item)]
    if isinstance(value, dict):
        return [passage for item in value.values() for passage in _passages(item)]
    return []


_QUOTES_AND_DASHES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "|": " "})
_WHITESPACE = re.compile(r"\s+")
# A PDF breaks "post-stroke" over two lines as "post-" and "stroke"; a model
# copying it joins them again. Both sides lose the space after a hyphen.
_HYPHEN_BREAK = re.compile(r"-\s+")


def _comparable(text: str) -> str:
    """Text reduced to what wording is: lower case, single spaces, plain quotes and dashes."""
    plain = _HYPHEN_BREAK.sub("-", text.translate(_QUOTES_AND_DASHES))
    return _WHITESPACE.sub(" ", plain).strip().lower()
