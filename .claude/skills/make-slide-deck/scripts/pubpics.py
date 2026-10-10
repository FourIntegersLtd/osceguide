"""pubpics.py platform|firestore <slide_id>... [--apply] (from api/, via poetry, PYTHONPATH=.)

Publishes refilm.py's new pictures and nothing else. Platform (run inside `railway run`, reads
RAILWAY_PROXY): sets each slide's image_urls and the deck's final_video_url on the existing media row.
Firestore (FIREBASE_SERVICE_ACCOUNT_KEY_PATH set): sets final_video_url on the existing document
(legacy decks carry no slide pictures). Every other field is left exactly as it is. Dry run without --apply.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pipe import R

API_SCRIPTS = Path(__file__).resolve().parents[4] / "api" / "scripts"

PUBLISHED = R / "published"


def _new(sid: str) -> dict:
    content = json.loads((PUBLISHED / f"{sid}.json").read_text(encoding="utf-8"))
    if not content["final_video_url"].endswith(f"{sid}_pictures.mp4"):
        sys.exit(f"{sid}: not refilmed yet")
    return content


async def _platform(sids: list[str], apply: bool) -> None:
    sys.path.insert(0, str(API_SCRIPTS))
    from railway_db import RAILWAY_PROXY, use_database_env
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.db import get_engine, import_all_models
    from app.features.media.models import MediaItem
    from app.migration.legacy_ids import legacy_row_id

    use_database_env(RAILWAY_PROXY)
    import_all_models()
    engine = get_engine()
    print("database host:", engine.url.host)
    async with AsyncSession(engine) as session:
        for sid in sids:
            new = _new(sid)
            row = await session.get(MediaItem, legacy_row_id(new["legacy_ref"]))
            if row is None:
                print(f"{sid}: MISSING row")
                continue
            content = json.loads(json.dumps(row.content))
            if len(content["slides"]) != len(new["slides"]):
                print(f"{sid}: SKIP slide count {len(content['slides'])} != {len(new['slides'])}")
                continue
            for slide, fresh in zip(content["slides"], new["slides"], strict=True):
                slide["image_urls"] = fresh["image_urls"]
            content["final_video_url"] = new["final_video_url"]
            if content == row.content:
                print(f"{sid}: already current")
                continue
            if apply:
                row.content = content
            print(f"{sid}: {'updated' if apply else 'would update'}")
        if apply:
            await session.commit()
    await engine.dispose()


def _firestore(sids: list[str], apply: bool) -> None:
    from dotenv import load_dotenv

    load_dotenv(".env")
    sys.path.insert(0, str(API_SCRIPTS))
    from import_b2c_media import configure_firebase_credentials_from_env

    from app.migration import b2c_firestore
    from app.migration.b2c_media_sources import B2C_MEDIA_SLIDE_COLLECTIONS

    configure_firebase_credentials_from_env()
    collection = b2c_firestore.client().collection(B2C_MEDIA_SLIDE_COLLECTIONS["sca"])
    for sid in sids:
        new = _new(sid)
        hits = list(collection.where("slide_id", "==", sid).limit(2).stream())
        if len(hits) != 1:
            print(f"{sid}: {len(hits)} documents, skipped")
            continue
        doc = hits[0].to_dict()
        if "final_video_url" not in doc:
            print(f"{sid}: document has no final_video_url, skipped")
            continue
        if doc["final_video_url"] == new["final_video_url"]:
            print(f"{sid}: already current")
            continue
        if apply:
            now = datetime.now(UTC)
            stamp = now.isoformat() if isinstance(doc.get("updated_at"), str) else now
            hits[0].reference.update({"final_video_url": new["final_video_url"], "updated_at": stamp})
        print(f"{sid}: {'updated' if apply else 'would update'} {hits[0].reference.path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", choices=("platform", "firestore"))
    parser.add_argument("slide_ids", nargs="+", metavar="slide_id")
    parser.add_argument("--apply", action="store_true", help="write; a dry run without it")
    args = parser.parse_args()
    sids, apply = args.slide_ids, args.apply
    if args.target == "platform":
        asyncio.run(_platform(sids, apply))
    else:
        if not os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"):
            sys.exit("FIREBASE_SERVICE_ACCOUNT_KEY_PATH is not set")
        _firestore(sids, apply)


if __name__ == "__main__":
    main()
