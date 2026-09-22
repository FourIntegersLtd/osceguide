"""Rules for an uploaded CV: what may be processed, and what it becomes.

Pure, and deliberately the *cheap* checks: they run before any PDF is parsed or
any model is called, so a file that was never going to be a CV costs nothing to
refuse. The retiring backend scattered these through its route; they are rules,
so they live here and the route stays thin.
"""

from __future__ import annotations

from enum import StrEnum

# The retiring backend's bounds. Ten megabytes is far more than a CV with text
# weighs and stops a large upload from being parsed in the request that took it.
MAX_BYTES = 10 * 1024 * 1024
MIN_BYTES = 1024
ALLOWED_SUFFIX = ".pdf"
# Fewer characters than this and there was nothing to read — a scan, or a file
# that is not a CV. Refused rather than sent to a model to invent sections from.
MIN_TEXT_CHARS = 50
# How many of a person's own CVs the list shows, most recent first.
RECENT_LIMIT = 10


class Status(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InvalidCv(Exception):
    """A file that cannot be processed as a CV. Mapped to `invalid_cv_file`."""


def validate_upload(*, filename: str, size: int) -> None:
    """Refuse a file that cannot be a CV, before any work is done on it."""
    if not filename.lower().endswith(ALLOWED_SUFFIX):
        raise InvalidCv("Only PDF files are allowed.")
    if size > MAX_BYTES:
        raise InvalidCv(f"File too large. Maximum size is {MAX_BYTES // (1024 * 1024)}MB.")
    if size < MIN_BYTES:
        raise InvalidCv("File too small to be a CV.")


def ensure_enough_text(text: str) -> str:
    """The extracted text, or a refusal when the PDF held nothing to read."""
    cleaned = (text or "").strip()
    if len(cleaned) < MIN_TEXT_CHARS:
        raise InvalidCv("That PDF contains too little text to read as a CV.")
    return cleaned
