"""Copy AV-related keys from backend/b2c-api/.env into platform-api/.env.

Maps B2C naming (AWS_ACCESS_KEY, AWS_S3_BUCKET_NAME) to platform Settings names.
Does not print secret values.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B2C_ENV = ROOT.parent / "b2c-api" / ".env"
PLATFORM_ENV = ROOT / ".env"

# b2c var -> platform var (pydantic-settings env names)
MAPPING = {
    "OPENAI_API_KEY": "OPENAI_API_KEY",
    "CARTESIA_API_KEY": "CARTESIA_API_KEY",
    "AWS_ACCESS_KEY": "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
    "AWS_S3_BUCKET_NAME": "AWS_S3_BUCKET",
    "AWS_REGION": "AWS_REGION",
}


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def write_env(path: Path, values: dict[str, str]) -> None:
    existing = parse_env(path) if path.is_file() else {}
    merged = {**existing, **values}
    lines = [f"{k}={v}" for k, v in sorted(merged.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    b2c = parse_env(B2C_ENV)
    if not b2c:
        print(f"No keys read from {B2C_ENV}", file=sys.stderr)  # noqa: T201
        return 1

    to_set: dict[str, str] = {}
    missing: list[str] = []
    for b2c_key, platform_key in MAPPING.items():
        val = b2c.get(b2c_key, "").strip()
        if not val:
            missing.append(b2c_key)
            continue
        to_set[platform_key] = val

    if missing:
        print("Missing in b2c .env (add there first):", ", ".join(missing), file=sys.stderr)  # noqa: T201

    if not to_set:
        print("Nothing to sync.", file=sys.stderr)  # noqa: T201
        return 1

    write_env(PLATFORM_ENV, to_set)
    print(f"Updated {PLATFORM_ENV} with: {', '.join(sorted(to_set))}")  # noqa: T201
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
