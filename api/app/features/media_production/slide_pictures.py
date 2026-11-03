"""Where a deck's pictures come from and where they are kept.

Wikimedia Commons is searched for wide, freely licensed files only. A picture that is chosen is
stored in this deployment's bucket, since a worker's disk does not last, and the renderer draws
only pictures from there or from the bundled library, never from anywhere else on the web.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.settings import Settings
from app.features.media_production.s3 import object_exists, s3_client, upload_args
from app.features.media_production.slide_scenes import ASSETS

logger = logging.getLogger(__name__)

# Under the folder finished videos are served from, so a learner's browser can read it too.
PICTURE_FOLDER = "teaching_videos/v2/pictures"
COMMONS = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks every client to say who it is.
USER_AGENT = "osceguide-slides/1.0 (https://osceguide.com)"
MIN_WIDTH = 700
MAX_SIDE = 1600
CANDIDATES = 5
# A contact sheet's tiles: large enough to judge a picture, small enough to send several at once.
_TILE = (480, 320)
_SHEET_COLUMNS = 3
_FREE = re.compile(r"(CC0|Public domain|PD|CC BY)", re.IGNORECASE)


@dataclass(frozen=True)
class Candidate:
    """One Commons file that may be used: where it is, whose it is and under what licence."""

    title: str
    url: str
    page: str
    author: str
    licence: str


def _clean(value: object) -> str:
    """Commons metadata without its markup or runs of spaces."""
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", str(value or ""))).strip()


def commons_search(http: httpx.Client, query: str) -> list[Candidate]:
    """The first few wide, freely licensed bitmaps Commons finds for `query`, best match first."""
    reply = http.get(
        COMMONS,
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrlimit": 20,
            "gsrsearch": f"{query} filetype:bitmap",
            "prop": "imageinfo",
            "iiurlwidth": MAX_SIDE,
            "iiprop": "url|size|extmetadata",
            "iiextmetadatafilter": "LicenseShortName|Artist",
        },
    )
    reply.raise_for_status()
    pages = sorted(reply.json().get("query", {}).get("pages", {}).values(), key=lambda page: page["index"])
    kept: list[Candidate] = []
    for page in pages:
        info = page["imageinfo"][0]
        details = info.get("extmetadata") or {}
        licence = _clean(details.get("LicenseShortName", {}).get("value"))
        # Non-commercial and no-derivatives licences rule out a paid product's cropped slide.
        if info["width"] < MIN_WIDTH or not _FREE.match(licence) or "NC" in licence or "ND" in licence:
            continue
        kept.append(
            Candidate(
                title=page["title"],
                url=info["thumburl"],
                page=info["descriptionurl"],
                author=_clean(details.get("Artist", {}).get("value"))[:80],
                licence=licence,
            )
        )
        if len(kept) == CANDIDATES:
            break
    return kept


def picture_prefix(settings: Settings) -> str:
    """The start of every stored picture's URL: nothing else on the web is drawn into a video."""
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{PICTURE_FOLDER}/"


def store_picture(settings: Settings, http: httpx.Client, candidate: Candidate) -> str:
    """Stores a Commons file in the bucket as a JPEG no larger than a frame needs, answering its URL."""
    fetched = http.get(candidate.url)
    fetched.raise_for_status()
    encoded = io.BytesIO(jpeg(Image.open(io.BytesIO(fetched.content))))
    name = f"{hashlib.sha256(candidate.page.encode()).hexdigest()[:20]}.jpg"
    s3_client(settings).upload_fileobj(
        encoded,
        settings.aws_s3_bucket,
        f"{PICTURE_FOLDER}/{name}",
        ExtraArgs=upload_args(f"{PICTURE_FOLDER}/{name}"),
    )
    return picture_prefix(settings) + name


def store_library_picture(settings: Settings, name: str) -> str:
    """Puts a bundled picture in the bucket under its own name unless it is there already, answering
    its URL: a published deck is drawn and shown from the bucket, never from this server's files."""
    key = f"{PICTURE_FOLDER}/{name}"
    if not object_exists(settings, key):
        with (ASSETS / "slides" / "images" / name).open("rb") as picture:
            s3_client(settings).upload_fileobj(
                picture, settings.aws_s3_bucket, key, ExtraArgs=upload_args(key)
            )
    return picture_prefix(settings) + name


def fetch_pictures(settings: Settings, slides: list[dict[str, Any]], deck_dir: Path) -> None:
    """Brings a deck's stored pictures into `deck_dir/pictures` for the renderer to draw.

    A picture that cannot be fetched is left out; its slide is drawn without one.
    """
    prefix = picture_prefix(settings)
    wanted = {
        str(url) for slide in slides for url in slide.get("image_urls") or [] if str(url).startswith(prefix)
    }
    if not wanted:
        return
    folder = deck_dir / "pictures"
    folder.mkdir(parents=True, exist_ok=True)
    client = s3_client(settings)
    for url in wanted:
        key = urlparse(url).path.lstrip("/")
        try:
            client.download_file(settings.aws_s3_bucket, key, str(folder / Path(key).name))
        except Exception:
            logger.warning("Could not fetch slide picture %s", url, exc_info=True)


def library_credits() -> dict[str, dict[str, Any]]:
    """The bundled pictures by file name, each with its author, licence and source."""
    folder = ASSETS / "slides" / "images"
    credits: dict[str, dict[str, Any]] = json.loads((folder / "CREDITS.json").read_text(encoding="utf-8"))
    return {name: credit for name, credit in credits.items() if (folder / name).exists()}


def jpeg(picture: Image.Image, longest: int = MAX_SIDE) -> bytes:
    """`picture` as JPEG bytes, shrunk to at most `longest` pixels a side."""
    copy = picture.convert("RGB")
    copy.thumbnail((longest, longest))
    encoded = io.BytesIO()
    copy.save(encoded, "JPEG", quality=80)
    return encoded.getvalue()


def contact_sheet(pictures: list[bytes]) -> bytes:
    """The pictures side by side, each labelled with its place in the list from 1, as one JPEG.

    A picture that cannot be read is a blank tile, so the numbers still match the list.
    """
    rows = -(-len(pictures) // _SHEET_COLUMNS)
    width, height = _TILE
    sheet = Image.new("RGB", (width * _SHEET_COLUMNS, height * max(1, rows)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=44)
    for index, picture in enumerate(pictures):
        left, top = (index % _SHEET_COLUMNS) * width, (index // _SHEET_COLUMNS) * height
        try:
            tile = Image.open(io.BytesIO(picture)).convert("RGB")
            tile.thumbnail((width - 8, height - 8))
            sheet.paste(tile, (left + (width - tile.width) // 2, top + (height - tile.height) // 2))
        except Exception:  # noqa: BLE001 - an unreadable picture is shown as a blank tile
            logger.warning("Could not read a candidate picture", exc_info=True)
        draw.rectangle((left, top, left + 64, top + 56), fill="black")
        draw.text((left + 12, top + 4), str(index + 1), fill="white", font=font)
    return jpeg(sheet)
