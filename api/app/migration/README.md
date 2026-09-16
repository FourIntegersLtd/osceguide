# migration

Moving the legacy data in. **Not a feature slice** — it has no routes, no
domain and no place in the layer order, and it is deleted once every tenant is
across.

## What it is

Pure transform functions with unit tests on fixtures shaped like the real
exports. Written before anyone points them at production data, so the awkward
decisions can be argued about on paper:

- **A consumer is up to five records.** Four Firestore user documents, one per
  product, each with its own `has_paid` and `plan_end_date`, plus possibly a
  `b2b_users` row. The merge key is the lowercased email — which is why
  `users.email` is `citext` and unique, so the database enforces what the
  transform assumes.
- **Entitlements are the union.** Somebody who bought SCA and PLAB keeps both.
  Expired grants come across too: "your access ended in March" is a better
  answer than an empty list.
- **Nobody's password is imported.** b2c stores bcrypt and b2b unsalted
  SHA-256; neither is argon2 and one is unsafe, so everybody resets.
- **An unknown `app_type` stops the import.** b2c defaults to SCA, which is how
  CASC came to be marked with a GP rubric. An import is the worst place to
  repeat that.
- **Imported feedback is tagged `legacy-b2c`** (decision D-5). b2c's production
  scorer was never the engine, so this must not be silently compared with engine
  output.
- **Turn ids are preserved, or derived deterministically.** They are the
  idempotency key, so re-running the import is a no-op rather than a duplicate.
- **A record with no email is reported, never dropped.** Losing somebody quietly
  is worse than failing loudly.

## Loading

`loader.py` is the facade; `load_people.py` and `load_attempts.py` do the work,
in that order, because a transcript names its author by Firestore document id
and only the people load can resolve that.

- **Nothing here commits.** The caller owns the transaction, so `--dry-run` is
  the same code path followed by a rollback rather than a second, untested one.
  The dry run therefore hits every constraint the real run will.
- **Re-runnable**, guarded by the natural keys the schema already enforces:
  `users.email`, `attempts.legacy_ref`, `(attempt_id, message_id)`,
  `(attempt_id, policy_version)`. A second pass reports zero created.
- **An imported attempt with no station-set entry is `practice`, not
  `set_station`.** The schema requires a `set_entry_id` for `set_station`, and
  claiming a kind while leaving its reference null is how b2b ended up with
  columns that mean nothing. The legacy `mock_id` and `station_id` are kept, so
  the linkage can be restored when the sets come across.
- **Somebody who signed up before their import keeps their password.** Only the
  platform-admin flag is re-asserted from the export.

## Verifying

`verify.py`, deliberately separate from the loader: a loader that miscounts
would otherwise report its own mistake as success.

- **Counts** catch a whole category going missing, and ignore rows made since
  the cutover by filtering on `legacy_ref`.
- **Spot hashes** catch what counts cannot — the right turns in the wrong
  order, truncated text, a transcript on the wrong attempt.

Each check in `tests/migration/test_verify.py` runs against a database damaged
on purpose, because a verifier nobody has seen fail is not a verifier.

## Running it

```bash
python scripts/migrate_legacy.py --export ./export --dry-run     # default
python scripts/migrate_legacy.py --export ./export --no-dry-run  # commits
python scripts/migrate_legacy.py --export ./export --verify-only
```

`--dry-run` is the default and has to be turned off deliberately. Exit status
is non-zero if a single record was a problem or a single check failed, so it
is safe in a pipeline.

The export is a directory of JSON arrays: `users.json` (the four `*_users`
collections concatenated, each document keeping its `app_type` and its `id`),
optionally `b2b_users.json`, `transcripts.json` and `feedbacks.json`.

## What is missing

Station sets, sittings and org data. The consumer path — people, entitlements,
attempts, transcripts and legacy feedback — is end to end. A real export is
still needed to size the run and to catch shapes the fixtures do not have; see
`docs/OPEN-QUESTIONS.md` M-1.
