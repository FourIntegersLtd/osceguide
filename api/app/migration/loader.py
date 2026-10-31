"""Writing the transformed records into Postgres.

Three properties matter more than speed, because this runs once against data
nobody can regenerate:

**Re-runnable.** A partial run, a fixed transform and a second pass must
update nothing rather than duplicate somebody's history. Every insert is
guarded by the natural key the schema already enforces — `users.email`,
`attempts.legacy_ref`, `(attempt_id, message_id)`,
`(attempt_id, policy_version)` — so the database, not this module, is what
makes a second run a no-op.

**Loud.** A record that cannot be loaded is collected into the report with the
reason. Skipping somebody quietly is worse than failing.

**Reversible until it is not.** Nothing here commits. The caller owns the
transaction, so a dry run is the same code path followed by a rollback rather
than a second, untested one — which means the dry run exercises every
constraint the real run will hit.

Order matters and is not negotiable: people first, because an attempt cannot
be attached to anybody until their legacy document ids are resolved.
"""

from __future__ import annotations

from app.migration.load_attempts import legacy_ref_for, load_attempts
from app.migration.load_people import (
    LEGACY_SOURCE_REF,
    backfill_legacy_passwords,
    exams_by_code,
    load_users,
)
from app.migration.report import LoadReport

__all__ = [
    "LEGACY_SOURCE_REF",
    "LoadReport",
    "backfill_legacy_passwords",
    "exams_by_code",
    "legacy_ref_for",
    "load_attempts",
    "load_users",
]
