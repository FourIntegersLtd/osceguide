"""One-way copy of B2C users into platform Postgres.

Reads from Firestore (read-only) or from a `users.json` export. Writes
`users` and `entitlements` rows only. Live B2C and Firestore are unchanged —
no deletes or updates at the source.

    poetry run python scripts/import_b2c_users.py --from-firestore --dry-run
    poetry run python scripts/import_b2c_users.py --from-firestore --no-dry-run
    poetry run python scripts/import_b2c_users.py --export ./export --no-dry-run
    poetry run python scripts/import_b2c_users.py --from-firestore --write-export ./export
    poetry run python scripts/import_b2c_users.py --from-firestore --collection sca --dry-run

Credentials: `GOOGLE_APPLICATION_CREDENTIALS`, `FIREBASE_SERVICE_ACCOUNT_KEY_PATH`
(same as b2c-api), or JSON in `FIREBASE_SERVICE_ACCOUNT_KEY` /
`GOOGLE_APPLICATION_CREDENTIALS_JSON`. Loads `backend/b2c-api/.env` for the path
when present (does not override platform-api `.env`).

`--dry-run` is the default: full load, then rollback.

Backfilling `users.engagement_email_sent_at` against a prod database that was
already imported before this column existed: re-run this script against
Firestore (`--from-firestore --no-dry-run`). `load_users` matches by email and
only fills a blank `engagement_email_sent_at` (`load_people._apply_profile`),
so a second run is safe — it changes nothing else about an already-imported
account, and only sets the column where a legacy record shows a prior send.
Do this, or the fresh column, before turning on `ENGAGEMENT_EMAIL_ENABLED`
in prod: otherwise the job's first run re-emails everyone legacy already
reached.
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
from app.migration import loader  # noqa: E402
from app.migration.b2c_user_sources import (  # noqa: E402
    read_users_from_export_dir,
    stream_b2c_user_documents,
    write_users_json,
)
from app.migration.load_legacy_b2c import load_legacy_payments, load_legacy_referrals  # noqa: E402
from app.migration.users import (  # noqa: E402
    MergedEntitlement,
    MergedLegacyPayment,
    MergedReferral,
    MergedUser,
    UnknownLegacyProduct,
    UnusableRecord,
    entitlements_for,
    legacy_payment_for,
    merge_users,
    normalize_email,
    referral_for,
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


def prepare_import(
    raw_documents: list[dict[str, Any]],
) -> tuple[
    list[MergedUser],
    list[MergedEntitlement],
    list[MergedLegacyPayment],
    list[MergedReferral],
    list[str],
]:
    usable: list[dict[str, Any]] = []
    problems: list[str] = []
    grants: list[MergedEntitlement] = []
    payments: list[MergedLegacyPayment] = []
    referrals: list[MergedReferral] = []

    for raw in raw_documents:
        doc_id = raw.get("id") or raw.get("user_id") or "?"
        email = normalize_email(raw.get("email"))
        if not email:
            problems.append(f"user {doc_id}: no email address")
            continue
        usable.append(raw)
        try:
            grants.extend(entitlements_for(raw))
            payment = legacy_payment_for(raw)
            if payment is not None:
                payments.append(payment)
            referral = referral_for(raw)
            if referral is not None:
                referrals.append(referral)
        except (UnusableRecord, UnknownLegacyProduct) as exc:
            problems.append(f"user {doc_id}: {exc}")

    try:
        merged = merge_users(usable)
    except UnusableRecord as exc:
        problems.append(str(exc))
        merged = []

    return merged, grants, payments, referrals, problems


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
        raw_documents = stream_b2c_user_documents(products=products)
    else:
        raw_documents = read_users_from_export_dir(export_dir)  # type: ignore[arg-type]

    print(f"documents read: {len(raw_documents)}")  # noqa: T201

    if write_export is not None:
        out = write_export / "users.json" if write_export.is_dir() else write_export
        write_users_json(out, raw_documents)
        print(f"wrote {out}")  # noqa: T201

    merged, grants, payments, referrals, transform_problems = prepare_import(raw_documents)
    for problem in transform_problems:
        print(f"  problem: {problem}")  # noqa: T201
    print(  # noqa: T201
        f"people to load: {len(merged)}; entitlements: {len(grants)}; "
        f"payments: {len(payments)}; referrals: {len(referrals)}"
    )

    import_all_models()
    engine = get_engine()
    async with AsyncSession(engine) as session:
        report, _legacy_ids, email_ids = await loader.load_users(session, merged, grants)
        pay_report = await load_legacy_payments(session, payments, user_ids=email_ids)
        ref_report = await load_legacy_referrals(session, referrals, user_ids=email_ids)
        report = report.merge(pay_report).merge(ref_report)
        for problem in report.problems:
            print(f"  problem: {problem}")  # noqa: T201
        print(report.summary())  # noqa: T201

        failed = bool(report.problems)
        if commit and not failed:
            await session.commit()
            print("committed")  # noqa: T201
        else:
            await session.rollback()
            if failed:
                print("rolled back: loader problems were reported")  # noqa: T201
            else:
                print("rolled back" if not commit else "rolled back: dry-run")  # noqa: T201

    await engine.dispose()
    return 1 if failed or transform_problems else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-firestore", action="store_true", help="read the four consumer user collections"
    )
    parser.add_argument(
        "--export",
        type=Path,
        default=None,
        help="directory containing users.json",
    )
    parser.add_argument(
        "--write-export",
        type=Path,
        default=None,
        help="when reading Firestore, also write users.json (file or directory)",
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
