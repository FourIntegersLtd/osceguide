# Architecture decision records

One file per decision, numbered, never edited after acceptance (supersede with a new one). Template: `0000-template.md`.

| # | Decision |
|---|---|
| 0001 | One greenfield backend replaces b2b-api and b2c-api |
| 0002 | Modular monolith of feature slices with enforced dependency direction |
| 0003 | Postgres; tenancy enforced in code, not RLS (superseded by 0008 for tooling) |
| 0004 | Platform-issued JWT with pluggable identity providers |
| 0005 | Errors are typed exceptions; one handler; one error shape |
| 0006 | Background jobs on procrastinate over Postgres |
| 0007 | Tests run against a real database; no in-memory store |
| 0008 | Plain SQL through psycopg; Supabase CLI owns migrations |
| 0009 | Test-driven, the way the LiveKit layer was rebuilt |
