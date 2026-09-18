# Architecture decision records

One file per decision, numbered, never edited after acceptance (supersede with a new one). Template: `0000-template.md`.

| # | Decision |
|---|---|
| 0001 | One greenfield backend replaces b2b-api and b2c-api |
| 0002 | Modular monolith of feature slices with enforced dependency direction |
| 0003 | Postgres; tenancy enforced in code, not RLS (tooling restored by 0013) |
| 0004 | Platform-issued JWT with pluggable identity providers |
| 0005 | Errors are typed exceptions; one handler; one error shape |
| 0006 | Background jobs on procrastinate over Postgres |
| 0007 | Tests run against a real database; no in-memory store |
| 0008 | Plain SQL through psycopg; Supabase CLI owns migrations (superseded by 0013) |
| 0009 | Test-driven, the way the LiveKit layer was rebuilt |
| 0010 | One attempts table, its own identity, engine as a dependency |
| 0011 | `exams` and `org_programmes` are two tables |
| 0012 | Entitlement is a record of access, separate from payment |
| 0013 | SQLAlchemy 2.0 and Alembic, reinstated (supersedes 0008) |
| 0014 | Social content is addressed to an audience, not just an exam |
| 0015 | Live screens are pushed as server-sent events, carrying whole read models |
| 0016 | Exams and rubrics are authored data, not shipped code |
| 0017 | An exam has an owner; an institution authors its own (extends 0011, 0016) |
| 0018 | A circuit runs itself, and every override is recorded (extends 0006, 0015) |
| 0019 | The tutor's material index is pgvector, in the same database (answers M-3) |
