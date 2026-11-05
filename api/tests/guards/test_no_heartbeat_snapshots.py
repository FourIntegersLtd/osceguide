"""A stream sends a snapshot on events, not on every heartbeat.

`snapshot_on_heartbeat=True` re-reads the whole read model for every open stream every few
seconds, so an exam day's board and console cost a full query set per watcher per tick. The
screens are pushed instead: every write that changes what they show announces itself
(`sittings.announcements`, including `attempt_progress` for an attempt moving on a slot).

Two streams legitimately still do it, because what they show changes without any event:
seat lapses in the voice queue are Redis TTLs, and the staff machinery view is a health probe.
The list only shrinks.
"""

from __future__ import annotations

import ast

from tests.guards._scan import APP_ROOT, parse, python_files, rel

ALLOWED = {
    "app/features/voice/service.py",
    "app/features/health/service.py",
}


def test_only_the_listed_streams_snapshot_on_every_heartbeat() -> None:
    offenders: list[str] = []
    for path in python_files(APP_ROOT):
        for node in ast.walk(parse(path)):
            if (
                isinstance(node, ast.keyword)
                and node.arg == "snapshot_on_heartbeat"
                and isinstance(node.value, ast.Constant)
                and node.value.value is True
                and rel(path) not in ALLOWED
            ):
                offenders.append(f"{rel(path)}:{node.value.lineno}")
    assert not offenders, f"snapshot_on_heartbeat=True outside the allow-list: {offenders}"
