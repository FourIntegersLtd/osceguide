"""One-way copies of legacy production data (consumer Firestore, b2b-api) into platform Postgres.

Nothing in the running API imports this package; only the `scripts/import_b2c_*`,
`migrate_legacy` and backfill scripts do. That makes this file the one door every
copy of real people's data walks through, so the staging refusal lives here.
"""

from __future__ import annotations

import os


def refuse_on_staging() -> None:
    """Stop before any real person's data can reach a staging database.

    Staging holds seeded test data only. `APP_ENV` is read straight from the
    environment rather than from `Settings`, so the refusal holds for a script
    that never builds them. Staging's database is reachable only from inside
    Railway's staging environment, where `APP_ENV=staging` is always set.
    """
    if os.getenv("APP_ENV", "").strip().lower() == "staging":
        raise RuntimeError(
            "Refusing to copy legacy production data with APP_ENV=staging: "
            "staging holds seeded test data only. Seed it with scripts/seed_platform.py."
        )


# Runs on the first `import app.migration...`, before any copy can start.
refuse_on_staging()
