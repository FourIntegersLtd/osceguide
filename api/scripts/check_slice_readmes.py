"""CI rule: every feature slice documents itself.

A slice without a README, or with one missing the required headings, fails
the build. The headings are the questions a new engineer asks first.
"""

from __future__ import annotations

import sys
from pathlib import Path

FEATURES = Path(__file__).resolve().parents[1] / "app" / "features"
REQUIRED = ("## Purpose", "## Aggregates & invariants", "## Routes", "## Jobs", "## Cross-slice dependencies")


def main() -> int:
    failures: list[str] = []
    for slice_dir in sorted(p for p in FEATURES.iterdir() if p.is_dir() and not p.name.startswith("_")):
        readme = slice_dir / "README.md"
        if not readme.exists():
            failures.append(f"{slice_dir.name}: missing README.md")
            continue
        text = readme.read_text()
        for heading in REQUIRED:
            if heading not in text:
                failures.append(f"{slice_dir.name}: README.md lacks '{heading}'")
    for line in failures:
        print(line)  # noqa: T201
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
