"""Object storage, as another slice may use it.

`s3.py` is this slice's own adapter; a slice above it asks here. Stations need
it for a case's images — an orthopaedic station is a radiograph and a question
about it — and going straight to the adapter would make the bucket's shape
every caller's business.
"""

from __future__ import annotations

from typing import Any, BinaryIO

from app.core import object_urls
from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
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


# How long a signed media link stays valid. Two hours: the longest deck video plus a pause or two and
# every seek in it (each Range request is checked against this one expiry), while a link someone
# shares is dead the same afternoon. A reload fetches fresh links; nothing stores them.
MEDIA_URL_TTL_SECONDS = 7200

# The folders a study-media read (decks, podcasts, summaries) may hand out. A media body is written
# by staff, but a key outside these is never ours to sign for a learner.
MEDIA_KEY_PREFIXES = ("teaching_videos/", "podcasts/")

_log = get_logger(__name__)
_warned_unsignable = False


def _warn_once_unsignable(reason: str) -> None:
    """Says once per process that links are being withheld, so a broken key cannot flood the log."""
    global _warned_unsignable  # noqa: PLW0603 - a process-wide "already said so" flag
    if not _warned_unsignable:
        _warned_unsignable = True
        _log.error("media_links_withheld", reason=reason)


def sign_urls(value: Any, *, prefixes: tuple[str, ...]) -> Any:
    """The value with each of our bucket's links under `prefixes` swapped for a signed, expiring one.

    For anything a learner or an author is shown. A link outside the bucket, outside `prefixes`, or
    under a public folder (`core.object_urls.PUBLIC_PREFIXES`) comes back unchanged. With no bucket
    configured the value is returned as it is. Signing is local arithmetic, so it works while the
    bucket is still public.

    When signing cannot be done (no credentials, or the signer fails) the link is replaced by an
    empty string, never left raw: once the bucket is private a raw link is dead anyway, and before
    then it would be the permanent link this exists to hide. The page still loads, minus that file.
    """
    settings = get_settings()
    if not is_configured(settings):
        return value
    can_sign = bool(settings.aws_access_key_id and settings.aws_secret_access_key)

    def sign_key(key: str) -> str:
        """One key's signed link, or an empty string when signing is impossible."""
        if not can_sign:
            _warn_once_unsignable("no AWS credentials")
            return ""
        try:
            return readable_url(settings, key, expires_in=MEDIA_URL_TTL_SECONDS)
        except Exception as error:  # noqa: BLE001 - botocore raises many types; a page must never 500 over a link
            _warn_once_unsignable(type(error).__name__)
            return ""

    return object_urls.sign_bucket_urls(
        value,
        bucket=settings.aws_s3_bucket,
        region=settings.aws_region,
        allowed_prefixes=prefixes,
        sign_key=sign_key,
    )


def remove_urls(value: Any) -> Any:
    """The value with every link on our bucket cut out, for text a model will read."""
    settings = get_settings()
    if not is_configured(settings):
        return value
    return object_urls.remove_bucket_links(value, bucket=settings.aws_s3_bucket, region=settings.aws_region)


def strip_urls(value: Any) -> Any:
    """The value with every signed link on our bucket cut back to the plain one that is stored.

    For anything about to be saved: a client that posts back what it was shown must not leave an
    expiring link in a row.
    """
    settings = get_settings()
    if not is_configured(settings):
        return value
    return object_urls.strip_signatures(value, bucket=settings.aws_s3_bucket, region=settings.aws_region)
