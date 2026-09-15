"""Write the OpenAPI document to openapi.json.

The frontend generates its TypeScript types from this file, so it is the
contract between the two codebases and is committed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "openapi-export")
os.environ.setdefault("WORKER_SECRET", "openapi-export")
os.environ.setdefault("REDIS_DISABLED", "1")

from app.main import create_app  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    spec = create_app().openapi()
    OUT.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT} ({len(spec.get('paths', {}))} paths)")  # noqa: T201


if __name__ == "__main__":
    main()
