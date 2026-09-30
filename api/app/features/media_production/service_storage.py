"""Object storage, as another slice may use it.

`s3.py` is this slice's own adapter; a slice above it asks here. Stations need
it for a case's images — an orthopaedic station is a radiograph and a question
about it — and going straight to the adapter would make the bucket's shape
every caller's business.
"""

from __future__ import annotations

from typing import BinaryIO

from app.core.settings import Settings
from app.features.media_production import s3


def is_configured(settings: Settings) -> bool:
    """Whether anything can be stored at all. No bucket, no uploads."""
    return bool(settings.aws_s3_bucket)


def put_object(settings: Settings, handle: BinaryIO, key: str) -> str:
    """Store a file and answer the URL it is readable at."""
    return s3.upload_fileobj(settings, handle, key)


def remove_object(settings: Settings, url: str) -> None:
    """Delete whatever a stored URL points at."""
    s3.delete_object(settings, url)


def remove_key(settings: Settings, key: str) -> None:
    """Delete whatever is stored at `key` — for a caller that holds a bare key
    (as `peer_practice`'s `recording_key` is stored), not the public URL
    `remove_object` expects."""
    s3.delete_key(settings, key)


def object_exists(settings: Settings, key: str) -> bool:
    """Whether something has been stored at `key` yet."""
    return s3.object_exists(settings, key)


def readable_url(settings: Settings, key: str, *, expires_in: int = 3600) -> str:
    """A temporary URL anything can read `key` through, credentials and all."""
    return s3.presigned_url(settings, key, expires_in=expires_in)
