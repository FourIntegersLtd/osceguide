"""Staging holds seeded test data only: every script copying legacy production data refuses to run there."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Every script that imports `app.migration`, found rather than listed, so a new
# copy script is covered the day it is added.
COPY_SCRIPTS = sorted(
    script_path.name
    for script_path in (PROJECT_ROOT / "scripts").glob("*.py")
    if "app.migration" in script_path.read_text(encoding="utf-8")
)


def test_the_copy_scripts_were_found() -> None:
    """Guards the glob above: an empty list would make the test below pass vacuously."""
    assert "import_b2c_all.py" in COPY_SCRIPTS
    assert "migrate_legacy.py" in COPY_SCRIPTS


@pytest.mark.parametrize("script_name", COPY_SCRIPTS)
def test_copy_script_refuses_on_staging(script_name: str) -> None:
    """Run the script as an operator would, with APP_ENV=staging, and expect the refusal."""
    staging_environment = {**os.environ, "APP_ENV": "staging"}
    completed_run = subprocess.run(  # noqa: S603 - fixed interpreter and a script from this repo
        [sys.executable, str(PROJECT_ROOT / "scripts" / script_name), "--help"],
        cwd=PROJECT_ROOT,
        env=staging_environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed_run.returncode != 0
    assert "Refusing to copy legacy production data with APP_ENV=staging" in completed_run.stderr
