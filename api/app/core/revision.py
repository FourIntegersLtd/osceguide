"""Optimistic concurrency for edits (B-15): refuse a write made from a stale read."""

from __future__ import annotations

from app.core.errors import Conflict


class StaleRevision(Conflict):
    """Someone saved this since the caller read it."""

    code = "stale_revision"
    default_message = "This was changed by someone else since you opened it. Reload and try again."


def ensure_current(expected: int | None, actual: int) -> None:
    """Refuse a write that names an older revision than the row has. No revision named, no check."""
    if expected is not None and expected != actual:
        raise StaleRevision()
