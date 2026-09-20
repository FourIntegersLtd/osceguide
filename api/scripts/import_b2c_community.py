"""One-way copy of B2C community into platform Postgres.

Reads questions, replies and station comments from Firestore (read-only) or from
`community.json`. Writes `posts` and `post_likes` only.

    poetry run python scripts/import_b2c_community.py --from-firestore --dry-run
    poetry run python scripts/import_b2c_community.py --from-firestore --no-dry-run
    poetry run python scripts/import_b2c_community.py --export ./export --no-dry-run

Run `import_b2c_users.py` first so legacy user ids resolve. Station comments
need stations imported (`import_b2c_stations.py`).

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
from app.migration.b2c_community import (  # noqa: E402
    CommunityTransformError,
    MigratedCommunityPost,
    community_from_document,
)
from app.migration.b2c_social_sources import (  # noqa: E402
    read_community_from_export_dir,
    stream_b2c_community_documents,
    write_community_json,
)
from app.migration.load_community import load_community  # noqa: E402
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


def transform_documents(raw_documents: list[dict[str, Any]]) -> tuple[list[MigratedCommunityPost], list[str]]:
    migrated: list[MigratedCommunityPost] = []
    problems: list[str] = []
    for raw in raw_documents:
        doc_id = (
            raw.get("question_id")
            or raw.get("reply_id")
            or raw.get("comment_id")
            or raw.get("id")
            or "?"
        )
        try:
            migrated.append(community_from_document(raw))
        except (CommunityTransformError, UnknownLegacyProduct) as exc:
            problems.append(f"community {doc_id}: {exc}")
    return migrated, problems


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
        raw_documents = stream_b2c_community_documents(products=products)
    else:
        raw_documents = read_community_from_export_dir(export_dir)  # type: ignore[arg-type]

    print(f"documents read: {len(raw_documents)}")  # noqa: T201

    if write_export is not None:
        out = write_export / "community.json" if write_export.is_dir() else write_export
        write_community_json(out, raw_documents)
        print(f"wrote {out}")  # noqa: T201

    migrated, transform_problems = transform_documents(raw_documents)
    degraded = sum(1 for m in migrated if m.warnings)
    if degraded:
        print(f"community flagged: {degraded}")  # noqa: T201
    for problem in transform_problems:
        print(f"  problem: {problem}")  # noqa: T201

    print(f"community posts to load: {len(migrated)}")  # noqa: T201

    import_all_models()
    engine = get_engine()
    async with AsyncSession(engine) as session:
        report = await load_community(session, migrated)
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
    parser.add_argument("--export", type=Path, default=None, help="directory containing community.json")
    parser.add_argument(
        "--write-export",
        type=Path,
        default=None,
        help="when reading Firestore, also write community.json (file or directory)",
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
