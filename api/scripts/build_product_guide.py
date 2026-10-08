"""Keep the product guide's "what can go wrong" rows true to the backend.

`docs/guides/how-osce-guide-works.html` (repo root) is a published, lay-language page
about the whole product. Each row of its "What can go wrong, and what you would see"
lists carries `data-code="<error code>"`. The backend's error vocabulary is the complete
list of refusals (`core.errors.error_codes`, published as the `ErrorResponse.code` enum),
so the page can be checked against it instead of written from memory.

    PYTHONPATH=. python scripts/build_product_guide.py inventory > inventory.json
        Every code with its HTTP status, when it happens (the class docstring), the
        sentence a person reads when the web has no copy of its own (`default_message`),
        the slice it belongs to and the routes that can answer with it (openapi `x-codes`).
        The writing sessions read this; nothing is generated into the page.

    PYTHONPATH=. python scripts/build_product_guide.py --check [--pin]
        Exit 1 if a code in the catalogue has no row on the page, or a row cites a code
        the catalogue no longer has. `--pin` also fails when the page's "Checked against"
        line does not name the current short HEAD; without it a stale pin is a warning.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("APP_ENV", "test")

OPENAPI = ROOT / "openapi.json"
GUIDE = ROOT.parent / "docs" / "guides" / "how-osce-guide-works.html"

DATA_CODE = re.compile(r'data-code="([a-z0-9_]+)"')
CHECKED_AGAINST = re.compile(r"Checked against[^<]*?\b([0-9a-f]{7,12})\b")


def _classes() -> list[type[Any]]:
    from app.core.errors import AppError
    from app.main import create_app

    create_app()  # imports every slice, so the hierarchy is complete
    out: list[type[Any]] = []

    def walk(cls: type[Any]) -> None:
        for sub in cls.__subclasses__():
            out.append(sub)
            walk(sub)

    walk(AppError)
    return out


def _routes_by_code() -> dict[str, list[str]]:
    spec = json.loads(OPENAPI.read_text())
    out: dict[str, list[str]] = {}
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            for status, resp in op.get("responses", {}).items():
                for code in resp.get("x-codes", []):
                    out.setdefault(code, []).append(f"{method.upper()} {path} -> {status}")
    return out


def inventory() -> list[dict[str, Any]]:
    routes = _routes_by_code()
    rows: dict[str, dict[str, Any]] = {}
    for cls in _classes():
        code = cls.code
        slice_ = cls.__module__.split(".")[2] if cls.__module__.startswith("app.features.") else "core"
        row = rows.setdefault(
            code,
            {
                "code": code,
                "status": cls.status,
                "when": " ".join((cls.__doc__ or "").split()),
                "says": cls.default_message,
                "slice": slice_,
                "classes": [],
                "routes": sorted(set(routes.get(code, []))),
            },
        )
        row["classes"].append(f"{cls.__module__}.{cls.__name__}")
    return sorted(rows.values(), key=lambda r: (r["slice"], r["code"]))


def catalogue() -> set[str]:
    from app.core.errors import error_codes
    from app.main import create_app

    create_app()
    return set(error_codes())


def check(pin: bool) -> int:
    if not GUIDE.exists():
        print(f"missing: {GUIDE}")  # noqa: T201
        return 1
    page = GUIDE.read_text()
    on_page = set(DATA_CODE.findall(page))
    known = catalogue()
    problems: list[str] = []
    for code in sorted(known - on_page):
        problems.append(f"no row on the page for {code}")
    for code in sorted(on_page - known):
        problems.append(f"page cites {code}, which the backend no longer raises")
    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - git on PATH, as in CI
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    ).stdout.strip()
    pinned = CHECKED_AGAINST.search(page)
    if pinned is None:
        problems.append('the page has no "Checked against <commit>" line')
    elif head and not head.startswith(pinned.group(1)[: len(head)]) and not pinned.group(1).startswith(head):
        msg = f'the page says "Checked against {pinned.group(1)}" but HEAD is {head}'
        if pin:
            problems.append(msg)
        else:
            print(f"warning: {msg}")  # noqa: T201
    for p in problems:
        print(p)  # noqa: T201
    print(f"{len(on_page & known)} of {len(known)} codes covered")  # noqa: T201
    return 1 if problems else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "inventory":
        json.dump(inventory(), sys.stdout, indent=1)
        sys.exit(0)
    if "--check" in args:
        sys.exit(check(pin="--pin" in args))
    print(__doc__)  # noqa: T201
    sys.exit(2)
