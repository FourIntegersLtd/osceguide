"""Copy every file the platform uses from the old bucket into the platform bucket. Nothing is deleted.

    PYTHONPATH=. poetry run python scripts/copy_to_platform_bucket.py          # dry run: what would be copied
    PYTHONPATH=. poetry run python scripts/copy_to_platform_bucket.py --live   # copy, then check every size

Where a file belongs comes from `app.migration.bucket_moves.platform_key`. The script is safe to run again
whenever: a file already at its destination with the same size is skipped, so the nightly legacy sync can
call it to catch up on whatever the legacy site has added since. Two sources for one destination (the first
platform writer and the legacy site both kept practice recordings) must have the same size or the script
refuses to copy that destination and says so.
"""

# ruff: noqa: T201
from __future__ import annotations

import argparse
import collections
import concurrent.futures

import boto3
from railway_db import bootstrap_app

bootstrap_app()

from app.core import bucket_layout  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.migration.bucket_copy import copy_one, list_bucket, plan_copies  # noqa: E402


def main() -> None:
    """Plan the copies, print the plan, and with `--live` do them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="copy for real (default: dry run)")
    arguments = parser.parse_args()
    settings = get_settings()
    client = boto3.client(
        "s3",
        region_name=bucket_layout.REGION,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    source, destination_bucket = bucket_layout.LEGACY_BUCKET, bucket_layout.BUCKET
    to_copy, conflicts = plan_copies(list_bucket(client, source), list_bucket(client, destination_bucket))
    by_folder = collections.Counter("/".join(destination.split("/")[:2]) for destination in to_copy)
    print(f"{len(to_copy)} files to copy; {len(conflicts)} conflicting destinations")
    for folder, count in sorted(by_folder.items()):
        print(f"  {folder}: {count}")
    for conflict in conflicts:
        print("  CONFLICT", conflict)
    if not arguments.live:
        return
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        futures = [
            pool.submit(copy_one, client, source, destination_bucket, old_key, new_key)
            for new_key, old_key in to_copy.items()
        ]
        problems = [problem for future in futures if (problem := future.result())]
    print(f"copied {len(to_copy)}; problems: {len(problems)}")
    for problem in problems:
        print(" ", problem)


if __name__ == "__main__":
    main()
