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
    """Upload an in-memory file. Same object URL shape as `upload_file` — avoids writing a
    request upload to a temp file first just to hand S3 a path."""
    client = s3_client(settings)
    client.upload_fileobj(handle, settings.aws_s3_bucket, key)
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"


def delete_object(settings: Settings, url: str) -> None:
    """Remove the object a stored URL points at."""
    key = urlparse(url).path.lstrip("/")
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
