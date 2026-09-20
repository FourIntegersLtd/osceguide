"""One-way copy of B2C study material into platform Postgres.

Reads summaries, blogs and slide decks from Firestore (read-only) or from a
`media.json` export. Derives `podcast` rows from summaries that carry
`podcast_url`. Writes `media_items` only. Live B2C and Firestore are unchanged.

    poetry run python scripts/import_b2c_media.py --from-firestore --dry-run
    poetry run python scripts/import_b2c_media.py --from-firestore --no-dry-run
    poetry run python scripts/import_b2c_media.py --export ./export --no-dry-run
    poetry run python scripts/import_b2c_media.py --from-firestore --write-export ./export

Credentials: same as `import_b2c_stations.py` (loads `backend/b2c-api/.env` for
Firebase path when present).

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
from app.migration.b2c_media_sources import (  # noqa: E402
    ALL_MEDIA_KINDS,
    MediaKindSource,
    read_media_from_export_dir,
    stream_b2c_media_documents,
    write_media_json,
)
from app.migration.load_media import load_media  # noqa: E402
from app.migration.media import (  # noqa: E402
    MediaTransformError,
    MigratedMedia,
    UnknownLegacyProduct,
    media_from_document,
)


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


def _kinds_from_arg(kind: str | None) -> list[MediaKindSource]:
    if kind is None or kind == "all":
        return list(ALL_MEDIA_KINDS)
    if kind == "slide":
        return ["slide_deck"]
    if kind in ALL_MEDIA_KINDS:
        return [kind]  # type: ignore[list-item]
    raise ValueError(f"unknown kind {kind!r}")


def transform_documents(
    raw_documents: list[dict[str, Any]],
) -> tuple[list[MigratedMedia], list[str]]:
    migrated: list[MigratedMedia] = []
    problems: list[str] = []
    for raw in raw_documents:
        doc_id = (
            raw.get("summary_id")
            or raw.get("blog_id")
            or raw.get("slide_id")
            or raw.get("id")
            or "?"
        )
        try:
            migrated.extend(media_from_document(raw))
        except (MediaTransformError, UnknownLegacyProduct) as exc:
            problems.append(f"media {doc_id}: {exc}")
    return migrated, problems


async def run(
    *,
    commit: bool,
    from_firestore: bool,
    export_dir: Path | None,
    write_export: Path | None,
    collection: str | None,
    kind: str | None,
) -> int:
    if from_firestore and export_dir is not None:
        raise SystemExit("Use --from-firestore or --export, not both.")
    if not from_firestore and export_dir is None:
        raise SystemExit("Pass --from-firestore or --export DIR.")

    kinds = _kinds_from_arg(kind)

    if from_firestore:
        _configure_firebase_credentials_from_env()
        products = [collection] if collection else None
        raw_documents = stream_b2c_media_documents(kinds=kinds, products=products)
    else:
        raw_documents = read_media_from_export_dir(export_dir)  # type: ignore[arg-type]
        if kind and kind != "all":
            allowed = set(kinds)
            raw_documents = [d for d in raw_documents if d.get("_media_kind") in allowed]

    print(f"documents read: {len(raw_documents)}")  # noqa: T201

    if write_export is not None:
        out = write_export / "media.json" if write_export.is_dir() else write_export
        write_media_json(out, raw_documents)
        print(f"wrote {out}")  # noqa: T201

    migrated, transform_problems = transform_documents(raw_documents)
    degraded = sum(1 for m in migrated if m.warnings)
    if degraded:
        print(f"media flagged: {degraded}")  # noqa: T201
    for problem in transform_problems:
        print(f"  problem: {problem}")  # noqa: T201

    print(f"media rows to load: {len(migrated)}")  # noqa: T201

    import_all_models()
    engine = get_engine()
    async with AsyncSession(engine) as session:
        report = await load_media(session, migrated)
        for problem in report.problems:
            print(f"  problem: {problem}")  # noqa: T201
        print(report.summary())  # noqa: T201

        all_problems = transform_problems + report.problems
        failed = bool(all_problems)
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
    parser.add_argument(
        "--export",
        type=Path,
        default=None,
        help="directory containing media.json",
    )
    parser.add_argument(
        "--write-export",
        type=Path,
        default=None,
        help="when reading Firestore, also write media.json (file or directory)",
    )
    parser.add_argument(
        "--collection",
        choices=("sca", "plab", "casc", "ortho"),
        default=None,
        help="limit Firestore read to one exam",
    )
    parser.add_argument(
        "--kind",
        choices=("all", "summary", "blog", "slide", "slide_deck"),
        default="all",
        help="which material kinds to import (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run everything and roll back (default). Pass --no-dry-run to commit.",
    )
    args = parser.parse_args()
    kind_arg = None if args.kind == "all" else args.kind
    raise SystemExit(
        asyncio.run(
            run(
                commit=not args.dry_run,
                from_firestore=args.from_firestore,
                export_dir=args.export,
                write_export=args.write_export,
                collection=args.collection,
                kind=kind_arg,
            )
        )
    )


if __name__ == "__main__":
    main()
