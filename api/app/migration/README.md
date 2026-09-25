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
- `stations.json` — optional; the four `*stations` collections concatenated, each document keeping its `app_type`. Loaded before attempts, because an attempt names the station it ran against.

## B2C station library (copy only)

One-way import into `stations` / `station_versions`. **Does not write to
Firestore** or change live consumer traffic.

```bash
cd backend/platform-api
poetry run python scripts/import_b2c_stations.py --from-firestore --dry-run
poetry run python scripts/import_b2c_stations.py --from-firestore --no-dry-run
poetry run python scripts/import_b2c_stations.py --export ./export --no-dry-run
poetry run python scripts/import_b2c_stations.py --from-firestore --write-export ./export
```

Requires consumer exams from `alembic upgrade head`. Idempotent on
`content->>'station_id'`. Credentials: `GOOGLE_APPLICATION_CREDENTIALS` or
`FIREBASE_SERVICE_ACCOUNT_KEY` (same as the consumer API).

## B2C users (copy only)

One-way import into `users` and `entitlements`. **Does not write to Firestore**
or change live consumer traffic. Merges on email when loading more than one
exam; use `--collection` to copy a single exam's collection first.

```bash
cd backend/platform-api
poetry run python scripts/import_b2c_users.py --from-firestore --dry-run
poetry run python scripts/import_b2c_users.py --from-firestore --no-dry-run
poetry run python scripts/import_b2c_users.py --export ./export --no-dry-run
poetry run python scripts/import_b2c_users.py --from-firestore --write-export ./export
poetry run python scripts/import_b2c_users.py --from-firestore --collection sca --dry-run
```

Requires consumer exams from `alembic upgrade head`. Idempotent on `users.email`
and legacy entitlements (`source_ref = legacy-import`). Passwords are not
imported (same rules as `migrate_legacy.py`).

## B2C study material (copy only)

One-way import into `media_items` (summaries, blogs, slide decks, and podcast
episodes derived from summaries with `podcast_url`). **Does not write to
Firestore** or change live consumer traffic.

```bash
cd backend/platform-api
poetry run python scripts/import_b2c_media.py --from-firestore --dry-run
poetry run python scripts/import_b2c_media.py --from-firestore --no-dry-run
poetry run python scripts/import_b2c_media.py --export ./export --no-dry-run
poetry run python scripts/import_b2c_media.py --from-firestore --write-export ./export
poetry run python scripts/import_b2c_media.py --from-firestore --kind summary --collection sca --dry-run
```

Requires consumer exams from `alembic upgrade head`. Idempotent on
`content->>'legacy_ref'`. Credentials: same as the station import.

### Podcast URLs on summaries already in Postgres

If summaries were imported before Firestore had `podcast_url`, or the first import
skipped existing rows, backfill from the summary collections:

```bash
poetry run python scripts/sync_b2c_podcast_urls.py --from-firestore --inspect
poetry run python scripts/sync_b2c_podcast_urls.py --from-firestore --no-dry-run
```

Updates `content.podcast_url` on summary rows and creates/updates `kind=podcast`
rows (`content.audio_url`). Read-only on Firestore.

## B2C community (copy only)

One-way import into `posts` and `post_likes` (questions, replies, station
comments). **Does not write to Firestore.**

```bash
cd backend/platform-api
poetry run python scripts/import_b2c_community.py --from-firestore --dry-run
poetry run python scripts/import_b2c_community.py --from-firestore --no-dry-run
```

Requires `import_b2c_users.py` (identity links) and, for station comments,
`import_b2c_stations.py`. Idempotent on deterministic row ids (uuid5 of
`{exam}:community:{kind}:{id}`). Credentials: same as media import.

## B2C marketplace (copy only)

One-way import into `availability_posts` and `peer_sessions`.

```bash
poetry run python scripts/import_b2c_marketplace.py --from-firestore --dry-run
poetry run python scripts/import_b2c_marketplace.py --from-firestore --purge-seeded --no-dry-run
```

`--purge-seeded` removes rows created through the live marketplace API (uuid4)
before copying Firestore; re-import is idempotent on uuid5 keys.

Requires `import_b2c_users.py`. Posts load before sessions. Idempotent on
uuid5 of `{exam}:marketplace:{post|session}:{id}`.

## B2C all collections (copy only)

One command that copies every consumer Firestore collection, in dependency
order, and refuses to run if Firestore holds a collection nobody has accounted
for. Firestore is only read (`collections()`, `stream()`).

```bash
poetry run python scripts/import_b2c_all.py --audit                # every collection, its count and fate
poetry run python scripts/import_b2c_all.py --skip-bad-records     # dry run (default)
poetry run python scripts/import_b2c_all.py --no-dry-run --skip-bad-records
poetry run python scripts/import_b2c_all.py --only attempts,debriefs
```

`b2c_inventory.py` is the list: each collection is either copied by a step or
skipped with a reason (runtime LiveKit state, reset tokens, `mocks` which have
no table, `help_*`, the legacy `b2b_*_v1` arm). Demo rows (`_seed_tag`,
`seed_` owners) are dropped on read.

The first five steps reuse the single-feature importers above. The rest are
new: transcripts and feedback into attempts (joined on `attempt_id`, linked to
the latest station version, with a `legacy-b2c` transcript row), debriefs, live
coverage, the `*_payments` collections, referral redemptions, partner arrivals
and reporters, CVs, contact messages and feature requests, and human practice
sessions.

People who deleted their account (`is_deleted`, email already scrubbed) are
not brought back: their transcripts are counted and skipped. Legacy transcript
quirks (double saves of one attempt, re-sent turns, one corrupt message id, NUL
characters) are straightened out in `b2c_transcript_cleanup.py` before loading.

`peer_practice` needs migration `n5o6p7q8r9s0` (recording columns) applied.

Each step runs in a savepoint. Without `--skip-bad-records` a step with any
problem rolls back whole, which is how three orphaned station comments kept
every community post out; with it, good rows land and bad ones are listed.
Every step is idempotent, so re-running copies only what is new.

## What is missing

Station sets, sittings and org data. The consumer path — people, entitlements,
attempts, transcripts and legacy feedback — is end to end. A real export is
still needed to size the run and to catch shapes the fixtures do not have; see
`docs/OPEN-QUESTIONS.md` M-1.
