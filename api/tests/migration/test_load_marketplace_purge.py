"""Purge of live API marketplace rows before a Firestore import."""

from __future__ import annotations

import uuid

from app.migration.legacy_ids import legacy_row_id
from app.migration.load_marketplace import _is_live_api_row_id


def test_legacy_import_ids_are_not_treated_as_seeded() -> None:
    imported = legacy_row_id("sca:marketplace:post:abc")
    assert not _is_live_api_row_id(imported)


def test_random_api_ids_are_seeded() -> None:
    live = uuid.uuid4()
    assert _is_live_api_row_id(live)
