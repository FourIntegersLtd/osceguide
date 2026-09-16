# 0002. Modular monolith of feature slices with enforced dependency direction

Date: 2026-09-15
Status: accepted

## Context
The legacy code organised by technical layer across the whole app (`routes/`, `services/`, `models/`), so one business change touched folders everywhere and nothing stopped a route from querying any collection. Microservices were considered and rejected: the scale does not justify network boundaries, separate deployments or distributed transactions.

## Decision
One deployable application organised as vertical feature slices under `app/features/`. Every slice has the same internal shape: `router`, `schemas`, `service`, `repository`, `domain`, `errors`, optional `jobs`, and a `README`. `app/core` is a shared kernel that never imports a slice. Slices depend on each other only through services and only downward in an order declared in `pyproject.toml`; `import-linter` fails CI on violations.

## Consequences
- Adding a domain means adding one directory and one migration.
- Cross-slice calls are visible and reviewable; an upward import is a design smell that surfaces immediately.
- If a slice ever needs to become its own service, its boundary already exists.
