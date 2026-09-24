from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlparse

import boto3

from app.core.settings import Settings


def s3_client(settings: Settings) -> Any:
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def upload_file(settings: Settings, local_path: Path, key: str) -> str:
    client = s3_client(settings)
    with local_path.open("rb") as handle:
        client.upload_fileobj(handle, settings.aws_s3_bucket, key)
    bucket = settings.aws_s3_bucket
    region = settings.aws_region
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def upload_fileobj(settings: Settings, handle: BinaryIO, key: str) -> str:
    """Upload an in-memory file. Same object URL shape as `upload_file`.

    A station photo arrives in the request rather than as a file on disk, and
    writing it to a temp file first only to hand S3 a path would be a round
    trip for nothing.
    """
    client = s3_client(settings)
    client.upload_fileobj(handle, settings.aws_s3_bucket, key)
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def delete_object(settings: Settings, url: str) -> None:
    """Remove the object a stored URL points at."""
    key = urlparse(url).path.lstrip("/")
    if not key:
        return
    s3_client(settings).delete_object(Bucket=settings.aws_s3_bucket, Key=key)
