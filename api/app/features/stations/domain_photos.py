"""Rules for a station's images: what may be uploaded, and where it lands.

Pure. Checking only the filename extension once left size unchecked server-side — a ten-megabyte
limit that existed only in the browser, so any caller that skipped it could post whatever it liked.
The size check is here.

Where an image lands is the template's call, not the exam's: the uploader
names a `media` block and the image is appended to that block's value, found
the same way `domain_content.content_for_template` reads it (a b2c station's
nested section first, then the flat block id). A new exam with scans needs a
media block in its template, never a branch here.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from app.core import bucket_layout

MAX_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})

# SEC-013: the leading bytes that make a file a PNG or a JPEG. The extension is
# only a claim the uploader makes; an .png that is really HTML or SVG would be
# served back inline from the images bucket and run in the viewer's origin.
# These are the signatures the browser itself trusts, so a file that does not
# begin with one is not the image it says it is.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
# Enough of the file to recognise either signature (PNG's is the longer, at 8).
SNIFF_BYTES = len(PNG_MAGIC)

# Where an upload lands: `station_images/<exam>/<fresh name>`. A fresh name per file: keying on
# `{username}/{original name}` let two authors uploading `xray.png` silently overwrite one another.
IMAGES_PREFIX = bucket_layout.STATION_IMAGES

# Before images were filed by exam, each upload went in a folder of its own station. Those photos stay
# where they are, so a station still signs its own folder.
KEY_PREFIX = bucket_layout.STATIONS.rstrip("/")


class InvalidPhoto(Exception):
    """A file that cannot be a station photo. Mapped to `invalid_photo`."""


def validate_upload(*, filename: str, size: int) -> None:
    """Refuse an upload by its declared name and size, before its bytes are even read."""
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix not in ALLOWED_SUFFIXES:
        raise InvalidPhoto("Only PNG and JPEG images are allowed.")
    if size > MAX_BYTES:
        raise InvalidPhoto(f"Image too large. Maximum size is {MAX_BYTES // (1024 * 1024)}MB.")
    if size <= 0:
        raise InvalidPhoto("That file is empty.")


def sniff_image(header: bytes) -> str | None:
    """The real type of an upload from its leading bytes, or None when it is
    neither a PNG nor a JPEG."""
    if header.startswith(PNG_MAGIC):
        return ".png"
    if header.startswith(JPEG_MAGIC):
        return ".jpeg"
    return None


def ensure_real_image(header: bytes) -> None:
    """Refuse a file whose bytes are not a PNG or a JPEG, whatever it is named.

    Paired with `validate_upload`, which trusts the extension: this is the half
    that checks the content, so a script renamed `x.png` cannot reach the bucket
    and be served back inline.
    """
    if sniff_image(header) is None:
        raise InvalidPhoto("That file is not a PNG or JPEG image.")


def key_prefixes(station_id: uuid.UUID) -> tuple[str, ...]:
    """The folders a station's read may sign links from: the per-exam image folders, and its own older
    folder. Another station's old photo, or any other file in the bucket, written into this station's
    content is not this station's to hand out."""
    return (
        f"{KEY_PREFIX}/{station_id}/",
        IMAGES_PREFIX,
    )


def object_key(*, exam_code: str, filename: str) -> str:
    """Where this upload lands in the bucket: the exam's image folder, a fresh name per file."""
    suffix = PurePosixPath(filename.lower()).suffix
    return f"{bucket_layout.exam_folder(IMAGES_PREFIX, exam_code)}/{uuid.uuid4().hex}{suffix}"


# The block type whose value is a list of media items: a URL, or `{url, kind, caption, alt}`.
MEDIA_TYPE = "media"


def media_section(sections: list[Any], block_id: str) -> str | None:
    """The id of the section holding `block_id`, when that block is a media block; otherwise None."""
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        for block in section.get("blocks") or []:
            if isinstance(block, Mapping) and block.get("id") == block_id and block.get("type") == MEDIA_TYPE:
                return str(section.get("id") or "")
    return None


def _slot(content: dict[str, Any], section_id: str, block_id: str) -> tuple[dict[str, Any], str]:
    """The dict a block's value lives in, and its key there.

    A b2c station keeps it inside the section's own dict, by the block id or
    the id without the section's prefix (`doctor_photos` is
    `doctor_information.photos`), and a value it does not hold yet goes in
    under the block id. A station without that section dict is flat.
    """
    nested = content.get(section_id)
    if not isinstance(nested, dict):
        return content, block_id
    bare = block_id.removeprefix(section_id.split("_", 1)[0] + "_")
    return nested, (bare if bare in nested and block_id not in nested else block_id)


def _item_url(item: Any) -> str | None:
    """A media item's URL, whether it is stored as a bare URL or as an object."""
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping) and isinstance(item.get("url"), str):
        return str(item["url"])
    return None


def with_media(content: dict[str, Any], *, section_id: str, block_id: str, url: str) -> dict[str, Any]:
    """The content with `url` appended to that media block. A single stored URL becomes a list of two."""
    updated = copy.deepcopy(content)
    holder, key = _slot(updated, section_id, block_id)
    current = holder.get(key)
    items = list(current) if isinstance(current, list) else ([current] if current else [])
    holder[key] = [*items, url]
    return updated


def without_media(content: dict[str, Any], sections: list[Any], *, url: str) -> tuple[dict[str, Any], bool]:
    """The content with that URL taken out of every media block, and whether it was ever on it.

    The second half is the check the retiring route did not make: it deleted
    whatever key the caller named, so any authorised user could pass any URL
    in the bucket and destroy it.
    """
    updated = copy.deepcopy(content)
    found = False
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        section_id = str(section.get("id") or "")
        for block in section.get("blocks") or []:
            if not isinstance(block, Mapping) or block.get("type") != MEDIA_TYPE or not block.get("id"):
                continue
            holder, key = _slot(updated, section_id, str(block["id"]))
            current = holder.get(key)
            if isinstance(current, list):
                kept = [item for item in current if _item_url(item) != url]
                if len(kept) != len(current):
                    holder[key] = kept
                    found = True
            elif _item_url(current) == url:
                holder[key] = []
                found = True
    return updated, found
