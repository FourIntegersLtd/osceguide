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

## What is missing

The loader and the `verify` step. Both need a real export to be worth writing
against — see `docs/OPEN-QUESTIONS.md` M-1. The transforms carry `legacy_ids`
so that verification can match rows back to the source.
