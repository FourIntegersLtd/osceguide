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

Find the legacy tests that cover this domain in `backend/b2b-api/tests/` and `backend/b2c-api/b2c/tests/`. Port their assertions against the new routes and services with the product vocabulary stripped: they are the oracle for behaviour that must survive. Where output must not change (a rendered prompt, a feedback payload, a cohort score, a report total), capture it from the legacy code into `tests/fixtures/` and assert the platform reproduces it byte-for-byte.

## 5. Domain (`tests/unit/` then `domain.py`)

Write unit tests for the invariants ("an attempt cannot go from `evaluated` back to `running`"), then write `domain.py` as plain Python: enums, dataclasses, state machines, policy predicates. No SQL, no FastAPI, no I/O. These tests need no database.

## 6. Tables and repository (`tests/repository/` then a migration and `repository.py`)

Write repository tests first: constraints that must hold, the lock that prevents a race, cursor pagination, and the mandatory test that org B cannot read org A's rows. Then declare the tables in `models.py`, run `make new-migration M="add_<slice>"` and **read what autogenerate wrote** — it misses constraint and index changes often enough that review is part of the step, not a courtesy. Then `repository.py`: one class per aggregate, `org_id` first on every org-scoped method, returning mapped objects or small dataclasses, never API schemas. Mapped classes stay inside the repository; a guard enforces it, because a lazy relationship can cross a tenant boundary with no visible query.

## 7. Service and router to green

`schemas.py`: request and response models (response models are mandatory; snake_case; never expose table rows directly). `service.py`: use cases that take the request connection, a principal or workspace, and any ports; raise `AppError` subclasses from `errors.py`; never commit. `router.py`: parse, call one service function, return the schema, declare errors with `error_responses(...)`. If a handler has an `if`, ask whether that rule belongs in the service.

## 8. Mount and document

- Add the router in `app/main.py` (the only place `include_router` is called).
- Add the slice to the layers list in `pyproject.toml` (`[tool.importlinter]`) in dependency order.
- Add a tag in `app/core/openapi.py`.
- Fill in `README.md` with the required headings (CI checks them).
- `make openapi` and commit `openapi.json`.
- Add an ADR under `docs/adr/` if you made a choice another engineer might question.

## Cross-slice rules

- Slice A may call slice B's **service**, never its repository, domain or models. Guarded by `tests/guards/test_slices_call_services_only.py`; if B's service has no function for what you need, that missing function is the point.
- There is no slice order: any slice may call any other slice's service. If two services would import each other at module load, import one inside the function that needs it.
- `app/core` never imports `app/features`.
- New external dependency: add a Protocol to `app/core/ports.py` and a fake to `tests/support/fakes.py` in the same commit. Never `patch("module.attribute")`.

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
