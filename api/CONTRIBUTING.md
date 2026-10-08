# Contributing: how to add a feature slice, tests first

This is the whole method. It is the one used to rebuild the LiveKit layer in `assessment-platform`: the guard test landed in the first commit, legacy tests were the oracle, golden fixtures froze what must not change, and no commit changed behaviour without a test beside it. Follow the steps in order; each produces something the next needs.

## The rule

**No behaviour change without a test in the same commit.** Guard tests first in the diff, then contract tests, then implementation. Deleting a capability deletes its test in the same commit and, where it matters, adds a guard that the file cannot return.

## 1. Write the use cases

Before any code, list what people do, in this form:

> As a **supervisor**, I **start a circuit** so that trainees can join their slots.
> As a **trainee**, I **see my results** once the org releases them.

Include the LiveKit worker as an actor where it calls the API. Nouns that recur become resources (`circuits`, `slots`, `results`). Verbs that are not create/read/update/delete become candidate actions (`start`). Put the list at the top of the slice README.

## 2. Guard tests (`tests/guards/`)

Write down what this slice must never do, as a scan that fails with the file name and the offending token, plus a meta-test that plants a violation and proves the scan catches it. The platform-wide guards already cover: core never imports features, SQL only in repositories, only `core/db.py` controls transactions, routers import only their own `schemas`/`service`/`errors`, a slice reaches another only through its `service*`/`schemas`/`errors`/`jobs`, every core `bind_*` seam is tied by `composition.py` and filled in a built app, org-scoped repository methods take `org_id` first, no legacy vocabulary, worker routes guarded, every route has a response model (or, for a `text/event-stream` route, a declared frame schema) and documented errors, and README headings. There is no file-length cap: split a file by responsibility, and merge micro-files when you touch them. Add a slice-specific guard only when the slice has a rule of its own (for example: the assistant content resolver never branches on exam outside the overlay registry).

## 3. Contract tests (`tests/http/`, `tests/contract/`)

Turn the use cases into HTTP tests against the schemas before any service exists: each route, its success shape, and each `ErrorResponse.code` it can return. Include a role × route access matrix for org-scoped slices. Use `mint_token(...)` from `tests/support/tokens.py`. These tests are the API design made executable; they stay red until step 7.

Naming rules the tests should encode:

- Plural kebab-case resources: `/station-templates`, `/trainee-groups`.
- Nest one level under the owner: `/orgs/{org_slug}/sessions/{id}`; deeper things get their own top-level path with a globally unique id (`/slots/{id}/feedback`).
- Action sub-resources only for state transitions with rules: `POST /circuits/{id}/start`. Everything else is `PATCH`.
- Lists return `Page[T]` with a cursor.
- Errors are `AppError` subclasses; the frontend switches on `code`, never on `message`.

## 4. Oracle and golden tests

Find the legacy tests that cover this domain in the old backend repository (`b2b-api/tests/`, `b2c-api/b2c/tests/`). Port their assertions against the new routes and services with the product vocabulary stripped: they are the oracle for behaviour that must survive. Where output must not change (a rendered prompt, a feedback payload, a cohort score, a report total), capture it from the legacy code into `tests/fixtures/` and assert the platform reproduces it byte-for-byte.

## 5. Domain (`tests/unit/` then `domain.py`)

Write unit tests for the invariants ("an attempt cannot go from `evaluated` back to `running`"), then write `domain.py` as plain Python: enums, dataclasses, state machines, policy predicates. No SQL, no FastAPI, no I/O. These tests need no database.

## 6. Tables and repository (`tests/repository/` then a migration and `repository.py`)

Write repository tests first: constraints that must hold, the lock that prevents a race, cursor pagination, and the mandatory test that org B cannot read org A's rows. Then declare the tables in `models.py`, run `make new-migration M="add_<slice>"` and **read what autogenerate wrote** — it misses constraint and index changes often enough that review is part of the step, not a courtesy. Then `repository.py`: one class per aggregate, `org_id` first on every org-scoped method, returning mapped objects or small dataclasses, never API schemas. Mapped classes stay inside the repository; a guard enforces it, because a lazy relationship can cross a tenant boundary with no visible query.

## 7. Service and router to green

`schemas.py`: request and response models (response models are mandatory; snake_case; never expose table rows directly). `service.py`: use cases that take the request connection, a principal or workspace, and any ports; raise `AppError` subclasses from `errors.py`; never commit. `router.py`: parse, call one service function, return the schema, declare errors with `error_responses(...)`. If a handler has an `if`, ask whether that rule belongs in the service.

## 8. Mount and document

- Add the router in `app/main.py` (the only place `include_router` is called).
- Add a tag in `app/core/openapi.py`.
- Fill in `README.md` with the required headings (CI checks them).
- `make openapi` and commit `openapi.json`.
- Add an ADR under `docs/adr/` if you made a choice another engineer might question.

## Cross-slice rules

- Slice A may call slice B's **service**, never its repository, domain or models. Guarded by `tests/guards/test_slices_call_services_only.py`; if B's service has no function for what you need, that missing function is the point.
- There is no slice order: any slice may call any other slice's service. If two services would import each other at module load, import one inside the function that needs it.
- `app/core` never imports `app/features`.
- New external dependency: add a Protocol to `app/core/ports.py` and a fake to `tests/support/fakes.py` in the same commit. Never `patch("module.attribute")`.

## Comments

Write for an engineer who knows Python but not this product. `tests/guards/test_code_is_documented.py` enforces the first two rules.

- Every file starts with a docstring of one to three plain sentences: what it is for and who it serves ("Starting, reading and finishing a candidate's attempt at a station.").
- Every function, method and class gets a docstring whose first line says what it does for a person or the system ("Lets a trainee see only the stations published to their org."). Add a second paragraph only for a why, a refusal, a side effect or an ordering constraint. Exempt: dunder methods, classes in `schemas*.py`, and one-line functions whose name says everything.
- **Route handlers, Pydantic models and enums get a `#` line above them, never a new docstring.** Their docstrings are published in `openapi.json`, so changing one changes the API document platform-web is generated from.
- Inline `#` comments only for a non-obvious why: a race, an ordering constraint, a workaround. A long function may carry a short comment before each step. Never narrate the next line.
- Describe people and outcomes ("the candidate can't restart a marked attempt"), not mechanics ("status transitions are guarded"). Use the words in `docs/GLOSSARY.md` exactly. History only in one clause, and only when it explains a constraint that still holds.
- British spelling. Delete comments that are stale, restate the code, or are TODOs with no owner.

## Naming

`tests/guards/test_names_are_descriptive.py` enforces the first rule.

- No single letters, loops and comprehensions included: `for station in stations`, `except ValueError as error`, `[membership.org_id for membership in memberships]`. Only `_` (a value thrown away) and `T` (a type variable) are allowed. Placeholders such as `data`, `obj`, `tmp`, `val` and `res` are refused too.
- Name a thing for what it is in product terms (`attempt`, `trainee_ids`, `score_percent`), not `row`, `result` or `item`. `row` is fine only in a helper that takes any table's row.
- No home-made abbreviations (`block_type`, not `btype`; `minimum`, not `mn`). Established ones stay: `org`, `id`, `db`, `url`, `stmt`.
- Functions are verbs that say the outcome (`claim_post`, `ensure_readable`); booleans read as yes or no (`is_live`, `has_rubric`); collections are plural; units go in the name (`duration_minutes`).
- **Never rename a contract:** route handler names (they become openapi operation ids and platform-web's client method names), query and path parameters, schema fields, table columns, JSON keys, env vars, error codes. Renaming a service function is fine when every caller moves in the same commit, with no alias left behind.

## Tests

| Folder | What | Needs DB |
|---|---|---|
| `tests/guards` | architecture rules, AST scans over `app/`, run alone in CI | no |
| `tests/unit` | `domain.py`, pure helpers, fakes | no |
| `tests/repository` | SQL behaviour, constraints, locks, isolation | yes |
| `tests/http` | routes through `httpx.AsyncClient` | yes |
| `tests/contract` | worker routes vs engine contracts | yes |
| `tests/e2e` | real LiveKit worker against this API; `-m e2e`, env-gated | yes + LiveKit |

`make guards` runs the guards alone. `make test` runs everything but e2e.

## Things that will bite you

- `poetry run pytest -q | tail -2` shows the last two lines, **not** the exit code, so a red suite looks green. Use `make test`, or check `$?`.
- Postgres is on **5433** and Redis on **6380**, not the defaults. Set `DATABASE_URL` for anything run outside `make`.
- A migrated database is empty: run `make seed-platform` (then without `--dry-run`) or every attempt is refused as `unknown_exam`.
- `git checkout <file>` is not an undo for uncommitted work. Commit before planting a violation to prove a guard fires.
- Scripted edits silently match nothing when `ruff format` has reflowed the line since you read it. Assert your anchor before writing.
- A green suite is not evidence a feature works. Ask what would fail if the feature were deleted, and check the running app.
