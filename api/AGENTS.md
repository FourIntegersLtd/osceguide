# platform-api — AGENTS.md

The one backend: consumer, institution and partner products. It replaces
`b2c-api` and `b2b-api`, which are retiring. Read `CONTRIBUTING.md` (how a
feature slice is built, tests first) and `docs/README.md` (the doc map) first.

## Rules

- **`core` never imports `features`.** import-linter enforces it (`make arch`).
  Slices have no order: any slice may call another's `service*` directly
  (ADR 0002, amended 2026-09-25). No `bind_*` seams between features.
- **Tests run against a real Postgres** (ADR 0007). No in-memory store, no
  mocked repository.
- **A migration and `docs/DATA-MODEL.md` change in the same commit.**
  `make data-model` fails otherwise.
- **ADRs are never edited** after acceptance; supersede with a new one.
- **B2B defines its own exams.** Platform exams are the consumer catalogue; an
  institution never waits on them (ADR 0017).
- Errors are `AppError` subclasses; clients branch on `code`, never `message`.
- **Per-exam behaviour lives in `exams.settings`** (`catalog.schemas.ExamSettings`):
  date label, session modes, station subtypes, generation prompts. Never branch
  on an exam code; `tests/guards/test_no_exam_code_branches.py` fails on it.

## Commands

```bash
docker compose up -d                           # Postgres :5433, Redis :6380 (not the defaults)
poetry run alembic upgrade head
poetry run python scripts/seed_platform.py     # `make seed-platform` is only a dry run
make start                                     # API on :8002
make worker                                    # background jobs
make ci                                        # lint, typecheck, arch, guards, test
make guards                                    # tests/guards only, fast
```

## Traps

- **One open draft per station.** `add_version` refuses a second (`draft_exists`), and deleting
  the last version deletes the station, so a screen must not assume the station survives a delete.
- **A migrated database is empty.** Until it is seeded, every attempt is
  refused `unknown_exam`, which looks like a worker or frontend bug. The exam
  must also be published with a rubric version.
- **Entitlement grants are not live grants.** `entitlements.list_for_user`
  returns revoked and expired rows too. A gate must filter on `live` and fail
  closed.
- **`trainee_id` means two things.** Circuit slots use `users.id`; result
  decisions use `trainees.id`.
- **Two response models with the same class name** make FastAPI qualify both
  in `openapi.json`, which renames a type platform-web already imports. Grep
  other slices before naming one.
- **Three failures that are not breakage:** `test_the_engine_only_needs_pydantic`
  fails when its file runs and passes selected by id (import order);
  `test_assistant_routes`/`test_voice_routes` fail while a local `.env` sets
  `LIVEKIT_AGENT_NAMESPACE` (run with it empty); `tests/migration` errors when
  run after `tests/repository`, so run it alone. DB tests silently skip without
  the docker services, and a pass then means nothing.
- **A push to `main` deploys staging, not production.** Production moves only
  through the "Promote api to production" workflow (it moves `production-api`), which is ask-first.
  Every deploy runs `alembic upgrade head`, so a migration must only add (a
  rollback keeps the new schema). See `docs/ENVIRONMENT.md`, "Staging and production".
- **Real data never goes to staging.** `app.migration` refuses to import under
  `APP_ENV=staging`; seed staging with `scripts/seed_platform.py` instead.
- **A one-off script outside pytest needs `PYTHONPATH=.`.** `poetry run python
  some_script.py` fails `ModuleNotFoundError: No module named 'app'` unless run
  as `PYTHONPATH=. poetry run python some_script.py` from `api`
  — pytest's own `pythonpath` config doesn't apply outside it. Needed to prove
  the E-4 erasure job against a real row rather than only through pytest.
- **A stored rubric structure is version 1 or version 2.** Never read
  `structure["domains"]` or `structure["scale"]`: read it through
  `rubrics.service.domain_titles` or `rubrics.domain.parse_structure`, which
  upgrade version 1 on read. The dashboard did, and a republished version 2
  rubric would have emptied it with every test green.
- The e2e run (`pytest -m e2e`) needs the LiveKit `livekit` (rtc) package in
  this venv; `aiohttp` and `livekit-api` are already locked dependencies, so
  remove only `livekit` afterwards. `tests/conftest.py` blanks `OPENAI_API_KEY`
  for every test; the e2e fixture alone restores it. A station with no
  `patient_information` (or template layout) renders degraded, is never frozen,
  and its attempt is silently never marked ("not queueing a marking" in the API
  log) while the e2e still passes: check the stored result, not the test.
- **Another slice imports only `service*`, `schemas`, `errors` and `jobs`**, a
  `domain.py` imports no other slice, and one slice's `schemas` may not import
  another's (`tests/guards`). A read shape two slices return goes in
  `app/core/schemas.py`; rubric arithmetic is `rubrics.service_scoring`.
- **A stored result payload is the marks alone**, validated by the rubric's
  derived schema (`additionalProperties: false`). The model is the row's
  `model_used` column; rows scored before 2026-09-30 also carry it in the payload.
- **A failed request rolls back the whole test's session, not just itself.**
  `tests/conftest.py`'s `override_get_session` hands every request in one HTTP
  test the same `db_session`. A 422, or any `AppError` with the default
  `persist_effects=False` (every plain 409), rolls it back — erasing a row a
  service call inserted directly into `db_session` and only `flush()`-ed, and
  expiring every ORM attribute already read off it, so reading one later
  raises `MissingGreenlet` far from the real cause. Capture ids into a plain
  variable as soon as you create the row, and put a request expected to fail
  after any request whose committed effect the test still relies on.
- **A rubric draft may be invalid.** Create and edit save any structure; only
  publish refuses. Read a version's `problems` (or `parse_structure` it) before
  treating a stored draft as markable; `service_marking.trial_rubric` does.
- **The evaluator runs the engine in a thread** (`asyncio.to_thread`); a
  cancelled caller cannot stop it. The trial stream drops its answer.
- **Cleaning up an e2e run's leftover rows: delete users before stations.**
  `attempts.user_id → users` and `assessment_results/transcripts/transcript_messages/refresh_chains
  .attempt_id or .user_id → …` all cascade, so deleting the e2e users alone
  removes their attempts and everything hung off them. But
  `attempts.station_version_id → station_versions` is `RESTRICT`, so deleting
  the e2e-created stations (which cascades to their `station_versions`) first
  fails while a live attempt still points at one. Delete the users, then the
  stations, in one transaction; check row counts by email/title and
  `created_at` before either delete, on the local docker DB only.
- **A mutation on a `Timestamps` row must `session.refresh()` it before
  returning, if the caller reads `updated_at`.** `onupdate=func.now()` runs in
  Postgres, so the ORM object is left expired after the `UPDATE`; reading the
  expired attribute outside the request's async context raises
  `MissingGreenlet` with a stack trace that points nowhere near the real cause.
  A create path that refreshes and an update path that doesn't is an easy
  split to miss — test a second write, not just the first.

## Owners

| Area | Owner agent | Proof recipe |
|---|---|---|
| `voice/`, `assistant/`, `tutor_memory/`, `attempts/` apart from scoring, and the parts of `sittings/` and `peer_practice/` that start a room or receive a transcript | `voice-station-owner` | `verify-voice-station` skill |
| Scoring (`attempts/` evaluator, jobs, renderer), `rubrics/`, `catalog/` exams, `reviews/scoring.py`, outcome computation in `results/`, the legacy oracles | `marking-owner` | `verify-marking` skill |
| `sittings/` (circuits, clock, edit), `roster/`, `tenancy/`, the review and decision workflow, programmes, org read models in `dashboard/` | `institution-owner` | `verify-institution` skill |
| `identity/`, `sso/`, `entitlements/`, `billing/`, `growth/`, `notifications/`, `inbox/` | `access-owner` | `verify-access` skill |
| `stations/`, `station_sets/`, `generation/`, `media/`, `media_production/`, `community/`, `marketplace/`, `peer_practice/`, `cv/`, `public_site/`, the `import_b2c_*` scripts | `content-owner` | `verify-content` skill |
| Learner read models in `dashboard/` | `platform-web-owner` | platform-web `verify` skill |

All live in the workspace root's `.claude/`. Where two claim a file, the
split is: voice starts rooms, marking computes scores, institution runs the workflow. When you change owned code
without the owner, still prove it with its recipe.

## Ask first

New Poetry dependencies, a new migration, deleting a route or anything auth.
