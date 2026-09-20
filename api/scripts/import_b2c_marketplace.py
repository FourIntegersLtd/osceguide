"""One-way copy of B2C marketplace into platform Postgres.

Reads availability posts and peer sessions from Firestore (read-only) or from
`marketplace.json`. Writes `availability_posts` and `peer_sessions` only.

    poetry run python scripts/import_b2c_marketplace.py --from-firestore --dry-run
    poetry run python scripts/import_b2c_marketplace.py --from-firestore --no-dry-run

Run `import_b2c_users.py` first so legacy user ids resolve.

`--dry-run` is the default: full load, then rollback.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("APP_ENV", "local")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")
_b2c_env = _ROOT.parent / "b2c-api" / ".env"
if _b2c_env.is_file():
    load_dotenv(_b2c_env, override=False)

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.db import get_engine, import_all_models  # noqa: E402
from app.migration.b2c_marketplace import (  # noqa: E402
    MarketplaceTransformError,
    MigratedAvailabilityPost,
    MigratedPeerSession,
    marketplace_from_document,
)
from app.migration.b2c_social_sources import (  # noqa: E402
    read_marketplace_from_export_dir,
    stream_b2c_marketplace_documents,
    write_marketplace_json,
)
from app.migration.load_marketplace import load_marketplace_posts, load_peer_sessions  # noqa: E402
from app.migration.report import LoadReport  # noqa: E402
from app.migration.users import UnknownLegacyProduct  # noqa: E402


def _configure_firebase_credentials_from_env() -> None:
    import json
    import tempfile

    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        key_path = (os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH") or "").strip()
        if key_path:
            resolved = Path(key_path).expanduser()
            if resolved.is_file():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)

    json_content = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") or os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    if not json_content or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    try:
        json.loads(json_content)
    except json.JSONDecodeError:
        return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        handle.write(json_content)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = handle.name


def transform_documents(
    raw_documents: list[dict[str, Any]],
) -> tuple[list[MigratedAvailabilityPost], list[MigratedPeerSession], list[str]]:
    posts: list[MigratedAvailabilityPost] = []
    sessions: list[MigratedPeerSession] = []
    problems: list[str] = []
    for raw in raw_documents:
        doc_id = raw.get("post_id") or raw.get("session_id") or raw.get("id") or "?"
        try:
            row = marketplace_from_document(raw)
        except (MarketplaceTransformError, UnknownLegacyProduct) as exc:
            problems.append(f"marketplace {doc_id}: {exc}")
            continue
        if isinstance(row, MigratedAvailabilityPost):
            posts.append(row)
        else:
            sessions.append(row)
    return posts, sessions, problems


async def run(
    *,
    commit: bool,
    from_firestore: bool,
    export_dir: Path | None,
    write_export: Path | None,
    collection: str | None,
) -> int:
    if from_firestore and export_dir is not None:
        raise SystemExit("Use --from-firestore or --export, not both.")
    if not from_firestore and export_dir is None:
        raise SystemExit("Pass --from-firestore or --export DIR.")

    if from_firestore:
        _configure_firebase_credentials_from_env()
        products = [collection] if collection else None
        raw_documents = stream_b2c_marketplace_documents(products=products)
    else:
        raw_documents = read_marketplace_from_export_dir(export_dir)  # type: ignore[arg-type]

    print(f"documents read: {len(raw_documents)}")  # noqa: T201

    if write_export is not None:
        out = write_export / "marketplace.json" if write_export.is_dir() else write_export
        write_marketplace_json(out, raw_documents)
        print(f"wrote {out}")  # noqa: T201

    posts, sessions, transform_problems = transform_documents(raw_documents)
    for problem in transform_problems:
        print(f"  problem: {problem}")  # noqa: T201

    print(f"marketplace posts to load: {len(posts)}; sessions: {len(sessions)}")  # noqa: T201

    import_all_models()
    engine = get_engine()
    async with AsyncSession(engine) as session:
        report = LoadReport()
        report = report.merge(await load_marketplace_posts(session, posts))
        report = report.merge(await load_peer_sessions(session, sessions))
        for problem in report.problems:
            print(f"  problem: {problem}")  # noqa: T201
        print(report.summary())  # noqa: T201

        all_problems = transform_problems + report.problems
        failed = bool(transform_problems)
        if commit and not failed:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("rolled back" if not commit else "rolled back: problems were reported")  # noqa: T201

    await engine.dispose()
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-firestore", action="store_true", help="read consumer collections")
    parser.add_argument("--export", type=Path, default=None, help="directory containing marketplace.json")
    parser.add_argument(
        "--write-export",
        type=Path,
        default=None,
        help="when reading Firestore, also write marketplace.json (file or directory)",
    )
    parser.add_argument(
        "--collection",
        choices=("sca", "plab", "casc", "ortho"),
        default=None,
        help="limit Firestore read to one exam",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run everything and roll back (default). Pass --no-dry-run to commit.",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            run(
                commit=not args.dry_run,
                from_firestore=args.from_firestore,
                export_dir=args.export,
                write_export=args.write_export,
                collection=args.collection,
            )
        )
    )


if __name__ == "__main__":
    main()
