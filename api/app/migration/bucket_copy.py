"""Copying the old bucket's files into the platform bucket: what to copy, and one checked copy.

Used by `scripts/copy_to_platform_bucket.py`, which holds the command line. Nothing here deletes or changes
a file; a copy that is already in place with the same size is skipped, so it can be run again at any time.
"""

from __future__ import annotations

import collections
import mimetypes
from typing import Any

from app.migration.bucket_moves import load_moves, platform_key

GENERIC_TYPES = {None, "", "binary/octet-stream", "application/octet-stream"}


def list_bucket(client: Any, bucket: str) -> dict[str, int]:
    """Every object in the bucket and its size."""
    sizes: dict[str, int] = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            if not item["Key"].endswith("/"):
                sizes[item["Key"]] = item["Size"]
    return sizes


def plan_copies(
    source_sizes: dict[str, int], destination_sizes: dict[str, int]
) -> tuple[dict[str, str], list[str]]:
    """Destination to source for what still needs copying, and the destinations two different files claim.

    `source_sizes` is the old bucket, `destination_sizes` what the platform bucket already holds.
    """
    moves = load_moves()
    sources: dict[str, list[str]] = collections.defaultdict(list)
    for key in source_sizes:
        destination = platform_key(key, moves)
        if destination:
            sources[destination].append(key)
    to_copy: dict[str, str] = {}
    conflicts: list[str] = []
    for destination, keys in sorted(sources.items()):
        if len({source_sizes[key] for key in keys}) > 1:
            conflicts.append(f"{destination} <- {keys}")
        elif destination_sizes.get(destination) != source_sizes[keys[0]]:
            to_copy[destination] = sorted(keys)[0]
    return to_copy, conflicts


def copy_one(
    client: Any, source_bucket: str, destination_bucket: str, source: str, destination: str
) -> str | None:
    """Copy one object between buckets and check its size; a generic content type gets a real one."""
    head = client.head_object(Bucket=source_bucket, Key=source)
    arguments: dict[str, Any] = {"MetadataDirective": "COPY"}
    guessed = mimetypes.guess_type(destination)[0]
    if head.get("ContentType") in GENERIC_TYPES and guessed:
        arguments = {"MetadataDirective": "REPLACE", "ContentType": guessed}
    client.copy_object(
        Bucket=destination_bucket,
        Key=destination,
        CopySource={"Bucket": source_bucket, "Key": source},
        **arguments,
    )
    copied = client.head_object(Bucket=destination_bucket, Key=destination)["ContentLength"]
    return None if copied == head["ContentLength"] else f"SIZE DIFFERS {source} -> {destination}"
