"""Deterministic UUIDs for one-way B2C imports.

Imported rows use uuid5 so a second run inserts nothing new. Live API rows
continue to use random uuid4.
"""

from __future__ import annotations

import uuid

# Fixed namespace for all legacy-derived primary keys in platform Postgres.
B2C_IMPORT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def legacy_row_id(legacy_ref: str) -> uuid.UUID:
    """The deterministic uuid5 primary key for one legacy reference, stable across re-runs."""
    return uuid.uuid5(B2C_IMPORT_NAMESPACE, legacy_ref.strip())
