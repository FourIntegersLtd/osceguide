"""Link Firestore `user_id` values as extra consumer identity subjects.

The first user import linked Firestore document ids only. B2C community and
marketplace reference the `user_id` field on user documents instead.

    poetry run python scripts/backfill_b2c_user_id_subjects.py --from-firestore --dry-run
    poetry run python scripts/backfill_b2c_user_id_subjects.py --from-firestore --no-dry-run
"""

from __future__ import annotations

import argparse
import asyncio
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
from app.features.identity import repository as identity_repository  # noqa: E402
from app.migration.b2c_user_sources import stream_b2c_user_documents  # noqa: E402
from app.migration.load_legacy_b2c import LEGACY_CONSUMER_PROVIDER  # noqa: E402


def _configure_firebase_credentials_from_env() -> None:
    import json
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


async def run(*, commit: bool) -> int:
    _configure_firebase_credentials_from_env()
    documents = stream_b2c_user_documents()
    print(f"user documents read: {len(documents)}")  # noqa: T201

    import_all_models()
    engine = get_engine()
    linked = 0
    skipped = 0
    missing_doc = 0
    problems: list[str] = []

    async with AsyncSession(engine) as session:
        for doc in documents:
            doc_id = str(doc.get("id") or "").strip()
            user_id = str(doc.get("user_id") or "").strip()
            if not doc_id or not user_id or user_id == doc_id:
                skipped += 1
                continue

            existing_user_id = await identity_repository.identity_by_subject(
                session, LEGACY_CONSUMER_PROVIDER, user_id
            )
            if existing_user_id is not None:
                skipped += 1
                continue

            doc_identity = await identity_repository.identity_by_subject(
                session, LEGACY_CONSUMER_PROVIDER, doc_id
            )
            if doc_identity is None:
                missing_doc += 1
                continue

            product = str(doc.get("app_type") or "").strip().lower() or None
            await identity_repository.link_identity(
                session,
                user_id=doc_identity.user_id,
                provider=LEGACY_CONSUMER_PROVIDER,
                subject=user_id,
                tenant_slug=product,
            )
            linked += 1

        print(  # noqa: T201
            f"linked {linked}; skipped {skipped}; no doc identity {missing_doc}; problems {len(problems)}"
        )
        if commit:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            print("rolled back")  # noqa: T201

    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-firestore", action="store_true", required=True)
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(commit=not args.dry_run)))


if __name__ == "__main__":
    main()
