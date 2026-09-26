"""Copy `podcast_url` from Firestore summary docs into platform `media_items`.

Firestore stores the listen URL on each summary document (`summaries` for SCA,
`plab_summaries`, `casc_summaries`, `ortho_summaries` — the A–Z study library).
The main media import skips rows that already exist, so podcasts imported
without a URL are not updated on a second run. This script backfills:

- `content.podcast_url` on summary rows
- `kind=podcast` rows (or updates `content.audio_url`)

Read-only on Firestore.

    poetry run python scripts/sync_b2c_podcast_urls.py --from-firestore --inspect
    poetry run python scripts/sync_b2c_podcast_urls.py --from-firestore --dry-run
    poetry run python scripts/sync_b2c_podcast_urls.py --from-firestore --no-dry-run
    poetry run python scripts/sync_b2c_podcast_urls.py --export ./export --inspect

Credentials: same as `import_b2c_media.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

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
    read_media_from_export_dir,
    stream_b2c_media_documents,
)
from app.migration.sync_media_podcasts import (  # noqa: E402
    inspect_summary_podcast_fields,
    sync_podcast_urls_from_documents,
)


def _configure_firebase_credentials_from_env() -> None:
    import tempfile

    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        key_path = (os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH") or "").strip()
        if key_path:
            resolved = Path(key_path).expanduser()
            if resolved.is_file():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)

    json_content = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") or os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_KEY"
    )
    if not json_content or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    try:
        json.loads(json_content)
    except json.JSONDecodeError:
        return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
        handle.write(json_content)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = handle.name


def _load_summaries(
    *,
    from_firestore: bool,
    export_dir: Path | None,
    collection: str | None,
) -> list[dict]:
    if from_firestore:
        _configure_firebase_credentials_from_env()
        products = [collection] if collection else None
        return stream_b2c_media_documents(kinds=["summary"], products=products)
    return [
        d
        for d in read_media_from_export_dir(export_dir)  # type: ignore[arg-type]
        if d.get("_media_kind") in (None, "summary")
    ]


async def run(
    *,
    commit: bool,
    inspect_only: bool,
    from_firestore: bool,
    export_dir: Path | None,
    collection: str | None,
) -> int:
    if from_firestore and export_dir is not None:
        raise SystemExit("Use --from-firestore or --export, not both.")
    if not from_firestore and export_dir is None:
        raise SystemExit("Pass --from-firestore or --export DIR.")

    documents = _load_summaries(
        from_firestore=from_firestore,
        export_dir=export_dir,
        collection=collection,
    )
    print(f"summary documents read: {len(documents)}")  # noqa: T201

    inspection = inspect_summary_podcast_fields(documents)
    print(json.dumps(inspection, indent=2))  # noqa: T201

    if inspect_only:
        return 0

    import_all_models()
    engine = get_engine()
    async with AsyncSession(engine) as session:
        report = await sync_podcast_urls_from_documents(session, documents)
        for problem in report.problems[:50]:
            print(f"  problem: {problem}")  # noqa: T201
        if len(report.problems) > 50:
            print(f"  … and {len(report.problems) - 50} more problems")  # noqa: T201
        print(report.summary())  # noqa: T201

        if commit and report.has_no_problems:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("rolled back" if not commit else "rolled back: problems were reported")  # noqa: T201

    await engine.dispose()
    return 1 if report.problems else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-firestore", action="store_true")
    parser.add_argument("--export", type=Path, default=None, help="directory with media.json")
    parser.add_argument(
        "--collection",
        choices=("sca", "plab", "casc", "ortho"),
        default=None,
        help="limit to one exam's summary collection",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="only count Firestore podcast_url fields; do not touch Postgres",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="default: run sync then rollback. --no-dry-run to commit.",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            run(
                commit=not args.dry_run and not args.inspect,
                inspect_only=args.inspect,
                from_firestore=args.from_firestore,
                export_dir=args.export,
                collection=args.collection,
            )
        )
    )


if __name__ == "__main__":
    main()
