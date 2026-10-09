#!/usr/bin/env python3
"""Add the fetched, S3-uploaded Commons images to stations. Additive only: existing images stay.

Run from api/ under Poetry. Dry run unless --apply.

    s3         uploads each manifest image to yahayakenny/commons/<station>/<file> (publicly
               readable) and records its `s3_url` in the manifest. An existing key is never overwritten.
    firestore  ortho_stations/<id>: `commons_images` gets every image with its credit; CC0 and
               public-domain URLs also join `additional_image_urls` (the legacy site shows those
               bare, with no caption, so attribution-licensed images stay out of it).
    platform   a new published version per station whose `additional_image_urls` gains
               {url, caption: credit, alt} objects. With --database-url-env RAILWAY_PROXY under
               `railway run -s platform-postgres[-production] -e <env>`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from commons_images import load_manifest, save_manifest  # same folder

API_SCRIPTS = Path(__file__).resolve().parents[4] / "api" / "scripts"
# Lower-cased prefixes of Commons' LicenseShortName for images that need no credit:
# "CC0", "CC0 1.0", "Public domain", "Public Domain Mark 1.0". Anything else is treated as
# needing attribution, so a new spelling errs towards keeping the image out of the bare list.
NO_ATTRIBUTION = ("cc0", "public domain")


def _entries(work: Path) -> dict[str, list[dict[str, Any]]]:
    """Per legacy station id, the images to add, each carrying its credit."""
    by_station: dict[str, list[dict[str, Any]]] = {}
    for m in load_manifest(work):
        if not m.get("s3_url"):
            sys.exit(f"{m['file']} has no s3_url: upload before publishing")
        by_station.setdefault(m["station_id"], []).append({
            "url": m["s3_url"],
            "kind": "image",
            "caption": f"{m.get('author') or 'Unknown author'}, {m['licence']}, via Wikimedia Commons ({m['page_url']})",
            "alt": (m.get("description") or m["file"].removeprefix("File:"))[:200],
            "licence": m["licence"],
            "licence_url": m.get("licence_url") or "",
            "author": m.get("author") or "",
            "source_url": m["page_url"],
            "commons_file": m["file"],
        })
    return by_station


def _merge(current: list[Any], new: list[dict[str, Any]]) -> list[Any]:
    """Current items untouched, then each new image whose URL is not already there."""
    urls = {i if isinstance(i, str) else i.get("url") for i in current}
    return list(current) + [e for e in new if e["url"] not in urls]


def _firestore_update(doc: dict[str, Any], new: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """The fields to write: every image with its credit in `commons_images`; only CC0 and
    public-domain URLs in the bare `additional_image_urls` the legacy site shows uncredited."""
    bare = list(doc.get("additional_image_urls") or [])
    bare += [e["url"] for e in new if e["licence"].lower().startswith(NO_ATTRIBUTION) and e["url"] not in bare]
    fields = {"commons_images": _merge(doc.get("commons_images") or [], new), "additional_image_urls": bare}
    return {k: v for k, v in fields.items() if v != (doc.get(k) or [])}


def _stations_by_document_id(rows: Any, docs: list[dict[str, Any]]) -> dict[str, tuple[Any, dict[str, Any]]]:
    """Platform (station id, content) per Firestore document id. The manifest keys on the document id;
    the platform import kept the document's own `station_id` field (a uuid) when it had one."""
    by_content_id = {str(content.get("station_id")): (sid, content) for sid, content in rows}
    content_ids = {d["id"]: str(d.get("station_id") or d["id"]) for d in docs}
    return {doc_id: by_content_id[cid] for doc_id, cid in content_ids.items() if cid in by_content_id}


# ---------- s3 ----------

def cmd_s3(args: argparse.Namespace) -> None:
    from botocore.exceptions import ClientError

    from app.core.settings import get_settings
    from app.features.media_production.s3 import s3_client

    work = Path(args.work)
    settings = get_settings()
    client, bucket = s3_client(settings), settings.aws_s3_bucket
    manifest = load_manifest(work)
    uploaded = 0
    try:
        for m in manifest:
            key = "yahayakenny/commons/" + m["local_path"].removeprefix("commons/")
            try:
                client.head_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                    raise
                if args.apply:
                    client.upload_file(str(work / m["local_path"]), bucket, key,
                                       ExtraArgs={"ContentType": m.get("mime") or "image/jpeg"})
                uploaded += 1
            m["s3_url"] = f"https://{bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
    finally:  # keep the URLs of what did upload, even if a later upload fails
        if args.apply:
            save_manifest(work, manifest)
    print(f"{uploaded} of {len(manifest)} {'uploaded' if args.apply else 'to upload (dry run)'}")


# ---------- firestore ----------

def cmd_firestore(args: argparse.Namespace, entries: dict[str, list[dict[str, Any]]]) -> None:
    from dotenv import load_dotenv

    load_dotenv(".env")
    from app.migration import b2c_firestore
    from app.migration.b2c_station_sources import B2C_STATION_COLLECTIONS

    collection = b2c_firestore.client().collection(B2C_STATION_COLLECTIONS[args.app_type])
    changed, missing = 0, []
    for station_id, new in entries.items():
        ref = collection.document(station_id)
        doc = ref.get().to_dict()
        if doc is None:
            missing.append(station_id)
            continue
        update = _firestore_update(doc, new)
        if not update:
            print(f"same    {station_id}")
            continue
        changed += 1
        print(f"{'write' if args.apply else 'would'}   {station_id}: {', '.join(f'{k} {len(v)}' for k, v in update.items())}")
        if args.apply:
            ref.update(update)
    print(f"{changed} documents {'updated' if args.apply else 'to update (dry run)'}")
    _fail_if("missing", missing)


def _fail_if(what: str, ids: list[str]) -> None:
    """Exit non-zero when stations were skipped, so a clean-looking run cannot hide them."""
    if ids:
        sys.exit(f"{len(ids)} stations {what}: {', '.join(ids)}")


# ---------- platform ----------

async def cmd_platform(args: argparse.Namespace, entries: dict[str, list[dict[str, Any]]]) -> None:
    sys.path.insert(0, str(API_SCRIPTS))
    if args.database_url_env:
        from railway_db import use_database_env

        use_database_env(args.database_url_env)
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.db import get_engine, import_all_models
    from app.core.errors import AppError
    from app.core.settings import get_settings
    from app.features.catalog.models import Exam
    from app.features.identity.models import User
    from app.features.stations.models import Station, StationVersion

    import_all_models()
    host = urlparse(get_settings().database_url).hostname or "?"
    print(f"database host: {host}")
    async with AsyncSession(get_engine()) as session:
        actor = (await session.scalars(
            select(User.id).where(User.is_platform_admin.is_(True)).order_by(User.email != args.actor_email, User.created_at)
        )).first()
        if actor is None:
            sys.exit("no platform admin to publish as")
        rows = (await session.execute(
            select(Station.id, StationVersion.content)
            .join(StationVersion, StationVersion.id == Station.current_version_id)
            .join(Exam, Exam.id == Station.exam_id)
            .where(Exam.code == args.app_type, Station.owner_kind == "platform", Station.org_id.is_(None))
        )).all()
        docs = json.loads((Path(args.work) / "stations.json").read_text(encoding="utf-8"))
        by_legacy = _stations_by_document_id(rows, docs)
        published, missing, refused = 0, [], []
        for legacy_id, new in entries.items():
            if legacy_id not in by_legacy:
                missing.append(legacy_id)
                continue
            station_id, content = by_legacy[legacy_id]
            current = content.get("additional_image_urls") or []
            merged = _merge(current, new)
            if merged == current:
                print(f"same    {legacy_id}")
                continue
            print(f"{'publish' if args.apply else 'would'} {legacy_id}: additional_image_urls {len(merged)}")
            if not args.apply:
                continue
            try:
                await _publish_one(session, station_id, {**content, "additional_image_urls": merged}, actor)
                published += 1
            except AppError as exc:  # a refusal (e.g. an open draft) skips that station; anything else aborts
                await session.rollback()
                refused.append(legacy_id)
                print(f"REFUSED {legacy_id}: {type(exc).__name__}: {exc}")
        print(f"{published} stations published" if args.apply else "dry run")
        _fail_if("missing", missing)
        _fail_if("refused", refused)


async def _publish_one(session: Any, station_id: Any, content: dict[str, Any], actor: Any) -> None:
    """A new version of a platform library station with `content`, published and committed."""
    from app.features.stations import service_versions

    draft = await service_versions.add_version(session, None, station_id)
    await service_versions.edit_version(session, None, station_id, draft.version, content=content)
    await service_versions.publish_version(session, None, station_id, draft.version, actor_id=actor, now=datetime.now(UTC))
    await session.commit()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", choices=("s3", "firestore", "platform"))
    p.add_argument("--work", default="../commons-work")
    p.add_argument("--app-type", default="ortho")
    p.add_argument("--apply", action="store_true", help="write (default is a dry run)")
    p.add_argument("--database-url-env", help="platform: e.g. RAILWAY_PROXY")
    p.add_argument("--actor-email", default=os.environ.get("COMMONS_ACTOR_EMAIL", ""),
                   help="platform: the admin recorded as publisher (default: earliest platform admin)")
    args = p.parse_args()
    if args.target == "s3":
        return cmd_s3(args)
    entries = _entries(Path(args.work))
    if args.target == "firestore":
        cmd_firestore(args, entries)
    else:
        asyncio.run(cmd_platform(args, entries))


if __name__ == "__main__":
    main()
