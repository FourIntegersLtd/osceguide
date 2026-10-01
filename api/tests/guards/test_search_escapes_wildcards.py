"""A search box matches what was typed, through `core.search.contains_text`.

A hand-built `column.ilike(f"%{search}%")` leaves `%` and `_` as wildcards, so
a search for `_` matches every row. `contains_text` escapes them. This refuses
any `ilike` in the app so the next list endpoint cannot bring the bug back.
`app/migration` is exempt: it matches legacy records, not typed text.
"""

from __future__ import annotations

from pathlib import Path

from tests.guards._scan import attribute_names, is_migration, python_files, rel


def uses_ilike(path: Path) -> bool:
    """Whether the file calls `.ilike` or `.like` on anything."""
    return bool({"ilike", "like"} & attribute_names(path))


def test_no_hand_built_search_pattern() -> None:
    """Every text search in `app/` goes through `contains_text`."""
    offenders = [rel(path) for path in python_files() if not is_migration(path) and uses_ilike(path)]
    assert offenders == [], f"Use app.core.search.contains_text instead of ilike/like: {offenders}"


def test_the_guard_catches_a_hand_built_pattern(tmp_path: Path) -> None:
    """An `ilike` is found; `contains_text` is not."""
    hand_built = tmp_path / "hand_built.py"
    hand_built.write_text('stmt.where(Station.title.ilike(f"%{search}%"))\n', encoding="utf-8")
    shared = tmp_path / "shared.py"
    shared.write_text("stmt.where(contains_text(Station.title, search))\n", encoding="utf-8")
    assert uses_ilike(hand_built) is True
    assert uses_ilike(shared) is False
