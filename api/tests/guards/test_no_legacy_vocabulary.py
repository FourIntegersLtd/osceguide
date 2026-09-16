"""The platform does not speak the legacy backends' vocabulary.

`app_type` was the string that keyed four Firestore collections per entity;
`b2c`/`b2b` were the product branch that the LiveKit rebuild removed; the
admin email list was authorisation by constant. If any of these appear in
platform code, an old design is growing back. The data-migration package is
the one quarantine, because it must read the old shapes to translate them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.guards._scan import APP_ROOT, code_tokens, offenders, python_files, rel

BANNED = (
    "app_type",
    "apptype",
    "collection_mapping",
    "firestore",
    "admin_user_emails",
    "local_store",
    "localstore",
    "b2c",
    "b2b",
)

QUARANTINE = APP_ROOT / "migration"


def platform_files() -> list[Path]:
    return [p for p in python_files(APP_ROOT) if QUARANTINE not in p.parents]


def test_there_is_code_to_scan() -> None:
    assert len(platform_files()) >= 10


@pytest.mark.parametrize("path", platform_files(), ids=lambda p: rel(p))
def test_no_legacy_vocabulary(path: Path) -> None:
    bad = offenders(code_tokens(path), BANNED)
    assert not bad, (
        f"{rel(path)} uses legacy vocabulary {bad}. Exams are rows in the exams table; products "
        "are memberships and entitlements; admins are a column on users."
    )


def test_the_guard_would_catch_a_leak(tmp_path: Path) -> None:
    leaky = tmp_path / "leaky.py"
    leaky.write_text(
        '"""Mentioning app_type in a docstring is fine."""\n'
        'def collection(app_type):\n    return COLLECTION_MAPPING[app_type]["user"]\n',
        encoding="utf-8",
    )
    assert offenders(code_tokens(leaky), BANNED) == ["app_type", "collection_mapping"]
