# Contributing: how to add a feature slice

This is the whole method. Follow it in order; each step produces something the next step needs.

## 1. Write the use cases

Before any code, list what people do, in this form:

> As a **supervisor**, I **start a circuit** so that trainees can join their slots.
> As a **trainee**, I **see my results** once the org releases them.

Nouns that recur become resources (`circuits`, `slots`, `results`). Verbs that are not create/read/update/delete become candidate actions (`start`). Put the list at the top of the slice README.

## 2. Model the domain (`domain.py`)

Write the rules as plain Python: enums, dataclasses, state machines, policy predicates. No SQLAlchemy, no FastAPI, no I/O. Ask "what must always be true?" and encode it here (an attempt cannot go from `evaluated` back to `running`; a trainee can only view their own slot). Unit-test this file first; these tests need no database.

## 3. Design the tables (`models.py` + migration)

Derive tables from the aggregates in step 2. Rules:

- uuid primary keys; org-scoped tables carry `org_id` with a foreign key.
- Real foreign keys for every relationship. Join tables instead of arrays or JSON lists of ids.
- JSONB only for genuinely document-shaped data (a frozen engine definition, a rendered payload).
- Extend `Base`, `UUIDPrimaryKey`, `Timestamps` from `app.core.db`.

Then `make revision M="add <slice>"`, read the generated migration, and fix anything autogenerate got wrong.

## 4. Write the repository (`repository.py`)

One class per aggregate. Every method on an org-scoped repository takes `org_id: UUID` as its first parameter. Repositories return ORM objects or simple tuples, never Pydantic schemas. Write repository tests against the real database, including one that proves org B cannot read org A's rows.

## 5. Define the API contract (`schemas.py`)

Request and response models. Response models are mandatory on every route. Field names are snake_case. Do not reuse ORM models as schemas: the API is a promise to the frontend and the table is a storage detail; they change for different reasons.

Naming rules:

- Plural kebab-case resources: `/station-templates`, `/trainee-groups`.
- Nest one level under the owner: `/orgs/{org_slug}/sessions/{id}`; deeper things get their own top-level path with a globally unique id (`/slots/{id}/feedback`).
- Action sub-resources only for state transitions with rules: `POST /circuits/{id}/start`. Everything else is `PATCH`.
- Lists return `Page[T]` with a cursor.

## 6. Write the service (`service.py`)

Use cases as functions or a small class. The service receives a session (the request's transaction), a principal or workspace, and any ports it needs. It raises `AppError` subclasses (define slice-specific ones in `errors.py`) and never returns status codes or `(ok, result)` tuples. It never calls `commit`; the request transaction commits when the handler returns.

## 7. Write the router (`router.py`)

Parse input, resolve dependencies, call one service function, return the schema. If a handler has an `if`, ask whether that rule belongs in the service. Declare error responses with `error_responses(...)` so OpenAPI documents them.

## 8. Mount and document

- Add the router in `app/main.py` (the only place `include_router` is called).
- Add the slice to the layers list in `pyproject.toml` (`[tool.importlinter]`) in dependency order.
- Add a tag in `app/core/openapi.py`.
- Fill in `README.md` with the required headings (CI checks them).
- `make openapi` and commit `openapi.json`.

## 9. Record decisions

If you made a choice another engineer might question, add an ADR under `docs/adr/` (copy the template).

## Cross-slice rules

- Slice A may call slice B's **service**, never its repository or models directly.
- Dependencies point downward only, in the order listed in `pyproject.toml`. If you need to go upward, you have found a missing concept; discuss it before adding an import.
- `app/core` never imports `app/features`.

## Tests

| Folder | What | Needs DB |
|---|---|---|
| `tests/unit` | `domain.py`, pure helpers | no |
| `tests/repository` | SQL behaviour, constraints, isolation | yes |
| `tests/http` | routes through `httpx.AsyncClient` | yes |
| `tests/contract` | worker routes vs engine contracts | yes |

External services are faked through `app/core/ports.py` protocols. Never `patch("module.attribute")`.
