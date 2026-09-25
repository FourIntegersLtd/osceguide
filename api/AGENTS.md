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
- The e2e run (`pytest -m e2e`) installs `aiohttp` and the LiveKit SDK. Remove
  them afterwards or `make typecheck` fails on `voice/adapter.py`.

## Owners

| Area | Owner agent | Proof recipe |
|---|---|---|
| `voice/`, `assistant/`, `tutor_memory/`, `attempts/` apart from scoring, and the parts of `sittings/` and `peer_practice/` that start a room or receive a transcript | `voice-station-owner` | `verify-voice-station` skill |
| Scoring (`attempts/` evaluator, jobs, renderer), `rubrics/`, `catalog/` exams, `reviews/scoring.py`, outcome computation in `results/`, the legacy oracles | `marking-owner` | `verify-marking` skill |
| `sittings/` (circuits, clock, edit), `roster/`, `tenancy/`, the review and decision workflow, programmes, org read models in `dashboard/` | `institution-owner` | `verify-institution` skill |
| `identity/`, `sso/`, `entitlements/`, `billing/`, `growth/`, `notifications/` | `access-owner` | `verify-access` skill |
| `stations/`, `station_sets/`, `generation/`, `media/`, `media_production/`, `community/`, `marketplace/`, `peer_practice/`, `cv/`, `public_site/`, the `import_b2c_*` scripts | `content-owner` | `verify-content` skill |
| Learner read models in `dashboard/` | `platform-web-owner` | platform-web `verify` skill |

All live in the workspace root's `.claude/`. Where two claim a file, the
split is: voice starts rooms, marking computes scores, institution runs the workflow. When you change owned code
without the owner, still prove it with its recipe.

## Ask first

New Poetry dependencies, a new migration, deleting a route or anything auth.
