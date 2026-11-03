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
- **A migration that creates a table enables RLS on it** (`ALTER TABLE x ENABLE ROW LEVEL SECURITY`, no policies); a test fails otherwise.
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

- **Peer practice and the marketplace gate on the trial window only.** Every route that queues, offers,
  claims, joins or takes a voice token calls `attempts.require_entitlement(..., window_only=True)`; a new peer
  route must too, or an expired trial can still practise. Peer attempts are not counted toward the 3x3 trial.
- **Access is only given by choosing a plan.** Staff have no route that grants or extends an entitlement
  outright (`POST /platform/users/{id}/payments` with a plan code is the only way; a blank amount is a free
  plan). That is what makes a plan's station cap always apply. Revoke stays. A 0 pence payment is not a sale:
  revenue, the paid facet and partner "paid" counts all require `amount_total_pence > 0`.
- **After an engine change, refresh the installed copy**: `poetry run pip install --force-reinstall --no-deps
  ../assessment/packages/osce_assessment`. `poetry install` keeps a same-version path copy, so api tests
  import the old engine.
- **A provider deprecation** (a model id shut down by OpenAI, Anthropic, Cartesia or Google) goes in
  the `RETIREMENTS` table in `tests/guards/test_model_retirements.py` the day it is announced; the
  guard fails any source using that id within 240 days of its shutdown.
- **Two response models with the same class name** make FastAPI qualify both
  in `openapi.json`, which renames a type platform-web already imports. Grep
  other slices before naming one.
- **A one-off script outside pytest needs `PYTHONPATH=.`.** `poetry run python
  some_script.py` fails `ModuleNotFoundError: No module named 'app'` unless run
  as `PYTHONPATH=. poetry run python some_script.py` from `api`
  — pytest's own `pythonpath` config doesn't apply outside it. Needed to prove
  the E-4 erasure job against a real row rather than only through pytest.
- **Another slice imports only `service*`, `schemas`, `errors` and `jobs`**, a
  `domain.py` imports no other slice, and one slice's `schemas` may not import
  another's (`tests/guards`). A read shape two slices return goes in
  `app/core/schemas.py`; rubric arithmetic is `rubrics.service_scoring`.
- **A failed request rolls back the whole test's session, not just itself.**
  `tests/conftest.py`'s `override_get_session` hands every request in one HTTP
  test the same `db_session`. A 422, or any `AppError` with the default
  `persist_effects=False` (every plain 409), rolls it back — erasing a row a
  service call inserted directly into `db_session` and only `flush()`-ed, and
  expiring every ORM attribute already read off it, so reading one later
  raises `MissingGreenlet` far from the real cause. Capture ids into a plain
  variable as soon as you create the row, and put a request expected to fail
  after any request whose committed effect the test still relies on.
- **A mutation on a `Timestamps` row must `session.refresh()` it before
  returning, if the caller reads `updated_at`.** `onupdate=func.now()` runs in
  Postgres, so the ORM object is left expired after the `UPDATE`; reading the
  expired attribute outside the request's async context raises
  `MissingGreenlet` with a stack trace that points nowhere near the real cause.
  A create path that refreshes and an update path that doesn't is an easy
  split to miss — test a second write, not just the first.

Area traps (drafts, entitlements, rubric versions, results, deploys, seeding, e2e) live in
`.claude/rules/<area>.md`, loaded when you touch those paths.
- A published library station is invisible to a normal reader until `stations.approved` is true (staff via `all_exams` bypass it; `published_counts_by_exam` never does). A test helper that writes `Station(status="published")` directly must set `approved=True`: the column has only a server default, so the row reads back false. Approve/revoke: `POST /platform/stations/{id}/approve|revoke-approval`; list the backlog with `scripts/report_unapproved_stations.py`.
- A paid file's bucket link is permanent. Return media or station content to a person only through `media_production.service_storage.sign_urls(value, prefixes=...)` (a station signs only `stations/<its id>/`, media only `teaching_videos/` and `podcasts/`: station content is author-written), and strip signatures on write (`service_storage.strip_urls`). Index text and prompts must not carry URLs (`service_storage.remove_urls` for the assistant prompt); a flat `ReadingBrief.text` is signed like any other station content. HTTP tests in `test_station_signed_urls.py` / `test_media_signed_urls.py` enforce it; the guard lists the files that may build a bucket link. Never store a signed link.

## Owners

Who owns which path: `.claude/OWNERS.md` (a guard, `tests/guards/test_ownership.py`, fails if a
file has no owner or two). Area notes: `.claude/rules/`.

| Area | Owner agent | Proof recipe |
|---|---|---|
| `voice/`, `assistant/`, `tutor_memory/`, `attempts/` apart from scoring | `attempt-engine-owner` | `verify-attempt-engine` skill |
| Scoring (`attempts/` evaluator, jobs, renderer), `rubrics/`, `catalog/` exams, `reviews/`, `results/`, the legacy oracles | `marking-owner` | `verify-marking` skill |
| `sittings/`, `roster/`, `tenancy/`, programmes, org read models in `dashboard/` | `institution-owner` | `verify-institution` skill |
| `identity/`, `sso/`, `entitlements/`, `billing/`, `growth/`, `notifications/`, `inbox/` | `access-owner` | `verify-access` skill |
| `stations/`, `station_sets/`, `generation/`, `media/`, `media_production/`, `community/`, `marketplace/`, `peer_practice/`, `cv/`, `public_site/`, the `import_b2c_*` scripts | `content-owner` | `verify-content` skill |
| `health/`, `alembic/`, `app/worker/`, platform-console files in `dashboard/` | `staff-console-owner` | `verify-staff-console` skill |
| Learner read models in `dashboard/` | `web-foundation-owner` | platform-web `verify` skill |

All live in the workspace root's `.claude/`. Work through the `build-feature` and `fix-bug`
skills. When you change owned code without the owner, still prove it with its recipe.

## Ask first

New Poetry dependencies, a new migration, deleting a route or anything auth.
