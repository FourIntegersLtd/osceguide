"""Rules for a station's images: what may be uploaded, and where it lands.

Pure. Checking only the filename extension once left size unchecked server-side — a ten-megabyte
limit that existed only in the browser, so any caller that skipped it could post whatever it liked.
The size check is here.

Where a photo goes on the document is not a preference: every reader in the
product — the candidate's brief, the ortho doctor screen, the management
review — already reads these exact keys, so the shape is fixed by what is
already rendering it.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath
from typing import Any

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

# The key a station's images live under. One folder per station, and a fresh
# name per file: keying on `{username}/{original name}` let two authors
# uploading `xray.png` silently overwrite one another.
KEY_PREFIX = "stations"


class InvalidPhoto(Exception):
    """A file that cannot be a station photo. Mapped to `invalid_photo`."""


def validate_upload(*, filename: str, size: int) -> None:
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


def object_key(*, station_id: uuid.UUID, filename: str) -> str:
    suffix = PurePosixPath(filename.lower()).suffix
    return f"{KEY_PREFIX}/{station_id}/{uuid.uuid4().hex}{suffix}"


def is_ortho_clinical(content: dict[str, Any], exam_code: str) -> bool:
    """Whether the ortho radiograph slot applies to this station."""
    return exam_code.strip().lower() == "ortho" and (
        str(content.get("station_type") or "clinical").strip().lower() == "clinical"
    )


def with_photo(content: dict[str, Any], *, url: str, exam_code: str) -> dict[str, Any]:
    """The content, with one more image on it, in the place its readers look.

    Ortho's first clinical image is the radiograph and the rest are additional
    — the retiring rule, kept because `OrthoDoctorScreen` renders those two
    fields separately and a photo in the wrong one is a photo nobody sees.
    Every other exam keeps its photos on the doctor's information.
    """
    updated = dict(content)
    if exam_code.strip().lower() == "ortho":
        if is_ortho_clinical(updated, exam_code) and not updated.get("radiograph_image_url"):
            updated["radiograph_image_url"] = url
            return updated
        additional = list(updated.get("additional_image_urls") or [])
        additional.append(url)
        updated["additional_image_urls"] = additional
        return updated

    doctor = dict(updated.get("doctor_information") or {})
    photos = list(doctor.get("photos") or [])
    photos.append(url)
    doctor["photos"] = photos
    updated["doctor_information"] = doctor
    return updated


def without_photo(content: dict[str, Any], *, url: str) -> tuple[dict[str, Any], bool]:
    """The content with that image removed, and whether it was ever on it.

    The second half is the check the retiring route did not make: it deleted
    whatever key the caller named, so any authorised user could pass any URL
    in the bucket and destroy it.
    """
    updated = dict(content)
    found = False

    if updated.get("radiograph_image_url") == url:
        updated["radiograph_image_url"] = None
        found = True

    additional = list(updated.get("additional_image_urls") or [])
    if url in additional:
        updated["additional_image_urls"] = [image_url for image_url in additional if image_url != url]
        found = True

    doctor = dict(updated.get("doctor_information") or {})
    photos = list(doctor.get("photos") or [])
    if url in photos:
        doctor["photos"] = [photo_url for photo_url in photos if photo_url != url]
        updated["doctor_information"] = doctor
        found = True

    return updated, found
