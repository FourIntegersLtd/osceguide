"""The raw S3 adapter behind AV production's storage: a thin wrapper over boto3 that
`service_storage.py` is the rest of the codebase's way of reaching.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import urlparse

import boto3

from app.core.settings import Settings

# What a file is served as, by its extension. A name outside this list is stored as a download rather
# than something a browser may render, so an odd upload can never run in the page.
_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def upload_args(key: str) -> dict[str, str]:
    """The `ExtraArgs` every upload carries: its type from the key's extension, and how to show it."""
    content_type = _CONTENT_TYPES.get(PurePosixPath(key.lower()).suffix)
    if content_type is None:
        return {"ContentType": "application/octet-stream", "ContentDisposition": "attachment"}
    return {"ContentType": content_type, "ContentDisposition": "inline"}


@lru_cache(maxsize=4)
def _client(region: str, access_key_id: str, secret_access_key: str) -> Any:
    """One client per credential set: building a boto3 client costs milliseconds, and signing a page
    of links would otherwise build one per link. SigV4 and the regional endpoint are pinned so a signed
    link points at `<bucket>.s3.<region>.amazonaws.com`, the same host the stored link and the web's
    media-src allow-list use, instead of the global host that answers a redirect."""
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
        config=boto3.session.Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )


def s3_client(settings: Settings) -> Any:
    """A boto3 S3 client built from the configured AWS credentials and region."""
    return _client(settings.aws_region, settings.aws_access_key_id, settings.aws_secret_access_key)


def upload_file(settings: Settings, local_path: Path, key: str) -> str:
    """Uploads a file already on disk and answers its public object URL."""
    client = s3_client(settings)
    with local_path.open("rb") as handle:
        client.upload_fileobj(handle, settings.aws_s3_bucket, key, ExtraArgs=upload_args(key))
    bucket = settings.aws_s3_bucket
    region = settings.aws_region
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def upload_fileobj(settings: Settings, handle: BinaryIO, key: str) -> str:
    """Upload an in-memory file. Same object URL shape as `upload_file` — avoids writing a
    request upload to a temp file first just to hand S3 a path."""
    client = s3_client(settings)
    client.upload_fileobj(handle, settings.aws_s3_bucket, key, ExtraArgs=upload_args(key))
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def delete_object(settings: Settings, url: str) -> None:
    """Remove the object a stored URL points at."""
    key = urlparse(url).path.lstrip("/")
    if not key:
        return
    s3_client(settings).delete_object(Bucket=settings.aws_s3_bucket, Key=key)


def delete_key(settings: Settings, key: str) -> None:
    """Remove the object stored at `key` directly, for a caller that holds the
    key itself rather than the public URL `delete_object` expects.

    A delete for a key that is not there is not an error — S3 already treats
    it as a no-op rather than raising `NoSuchKey` — so a caller like the
    erasure job that must not fail its whole run over one recording that is
    already gone needs nothing extra here.
    """
    if not key:
        return
    s3_client(settings).delete_object(Bucket=settings.aws_s3_bucket, Key=key)


def object_exists(settings: Settings, key: str) -> bool:
    """Whether `key` is in the bucket yet. Egress writes the recording after the stop is
    acknowledged, so a caller that does not check may find nothing yet."""
    client = s3_client(settings)
    try:
        client.head_object(Bucket=settings.aws_s3_bucket, Key=key)
    except client.exceptions.ClientError:
        return False
    return True


def presigned_url(settings: Settings, key: str, *, expires_in: int) -> str:
    """A URL that grants a read of one object for a while. The bucket is private, so anything
    fetching an object without credentials of its own is handed one of these instead."""
    return str(
        s3_client(settings).generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_s3_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    )
