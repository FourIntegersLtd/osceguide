# Legacy sync: keep the new platform current with the old B2C site

Until everyone has moved off the old B2C site (Firestore), new sign-ups, practice
attempts, payments and feedback keep landing there. This sync copies **only what is new
or changed** into the platform database. It never re-imports everything.

Code: `app/migration/b2c_sync.py` (the ledger and the pending-only client),
`app/migration/b2c_steps.py` (the loaders, shared with the one-off import),
`scripts/sync_b2c.py` (the command), `scripts/sync_b2c_nightly.sh` (the wrapper the
Mac runs), `scripts/sync_b2c_now.sh` (the one you run by hand).

## How it knows what is pending

The table `legacy_sync_records` is a ledger: one row per old-site document that has been
copied, with the `update_time` it had then. Each run:

1. Lists every document id and `update_time` in the old collections (no bodies, a few seconds).
2. Pending = not in the ledger, or `update_time` newer than the ledger's value.
3. Fetches only the pending documents by id and runs the normal loaders on them.
4. Records what it served in the ledger, in the same transaction as the copy.

Loaders are add-only and idempotent (deterministic ids, natural keys such as
`attempts.legacy_ref`), so a repeat can never duplicate a row.

## Run it yourself (any time, for example before the 03:00 job)

```bash
cd ~/Documents/Projects/osceguide/api
scripts/sync_b2c_now.sh              # production: preview, asks y/N, then copies
scripts/sync_b2c_now.sh staging      # the same against staging
scripts/sync_b2c_now.sh --yes        # production without the question
```

The preview writes nothing. It prints a table (in old site / copied / pending / settling),
then the rows it would add per table. The copy prints "rows added" per table: that table is
the truth. (The loader's own "coverage created N" line counts rowcount and can overstate.)

Lower level, same thing: `scripts/sync_b2c_nightly.sh production [--dry-run]
[--baseline-before ISO_TIME]`. Log: `~/Library/Logs/osce-legacy-sync.log`.

## First run on an environment (baseline)

An empty ledger would offer all ~32,000 documents. The command **refuses** a real run with
an empty ledger unless you say when the last full import happened:

```bash
scripts/sync_b2c_nightly.sh production --dry-run --baseline-before 2026-11-02T16:00:00+00:00
scripts/sync_b2c_nightly.sh production           --baseline-before 2026-11-02T16:00:00+00:00
```

The last full import ran 2 Nov 2026, 16:34 to 22:02 UTC; the baseline is set earlier on
purpose. Everything last updated before it is recorded as already copied, without being
read. Everything after it is pending. Do this once per environment, then never again.

## The nightly job

`scripts/com.osceguide.legacy-sync.plist` runs `sync_b2c_nightly.sh production` at 03:00.

```bash
cp scripts/com.osceguide.legacy-sync.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.osceguide.legacy-sync.plist   # install
launchctl kickstart gui/$(id -u)/com.osceguide.legacy-sync                                 # run now
launchctl bootout gui/$(id -u)/com.osceguide.legacy-sync                                   # remove
tail -40 ~/Library/Logs/osce-legacy-sync.log
```

## Caveats

- **Migrate first.** A real run needs the table: `alembic upgrade head` (the api promote
  does this). Without it the command stops with "run `alembic upgrade head` first".
- **Baseline once** (above). An empty ledger without `--baseline-before` is refused.
- **The Mac must be on and signed in.** A Mac asleep at 03:00 runs the missed job when it
  wakes; a Mac that is off runs nothing. The job needs `railway login` and the Railway
  project link to still work. If the log says unauthorised, run `railway login`.
- **Documents changed in the last 30 minutes wait for the next run** (`--settle-minutes`),
  so a half-written document is not copied.
- **Problem records are reported once.** A document that cannot be loaded (a data oddity)
  is printed and recorded so it is not retried every night. Editing it on the old site
  makes it pending again. A database error rolls the step back and records nothing.
- **Context is read in full, read-only.** To join attempts to feedback the run reads all
  transcripts, feedbacks and mocks. Only pending (or dirty) documents are written.
- **Firestore is never written.** Credentials come from
  `GOOGLE_APPLICATION_CREDENTIALS` (the service account key; set by the wrapper).
- **Deleted accounts are skipped**, and transcripts of grants already revoked are not reopened.
- **Staging is not a full mirror.** Its preview shows what staging lacks, which is a lot.
  Production is the real target.
- **Never print secrets.** The wrapper passes the database to the command through
  `railway run`; do not echo environment variables into the log.
- **Retirement.** When the old site is switched off, drop `legacy_sync_records` with the
  legacy copy and remove the launchd job.
