from __future__ import annotations

from pathlib import Path
from typing import Any

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
