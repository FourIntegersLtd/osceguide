# 0001. One greenfield backend replaces b2b-api and b2c-api

Date: 2026-09-15
Status: accepted

## Context
Two backends served one product family. `b2b-api` (FastAPI, Supabase client) had sound layering but weak plumbing: no transactions, hand-applied SQL migrations, services returning `(ok, result)` tuples with handlers guessing HTTP codes from message text, and an in-memory shadow store that most tests ran against instead of the database. `b2c-api` (Flask, Firestore) had grown into RPC-style routes with business logic inside 1,600-line handler files, four Firestore collections per entity keyed by `app_type`, and no job queue behind minutes-long AI calls. Roughly 2,200 lines of feedback models plus the LiveKit routing, capacity, worker-guard and attempt-adaptation modules were duplicated between them. The LiveKit layer had just been rebuilt as one consumer-agnostic engine, which made the two-backend split the last remaining duplication.

Target scale (year 5: about 12k new consumer subscriptions a month and about 120 institutions) is a single-Postgres workload.

## Decision
Build one new backend, `platform-api`, and migrate both products into it slice by slice. Evolving `b2b-api` was rejected because its data layer, error convention and test strategy all needed replacing, which is most of the code.

## Consequences
- One codebase, one deployment pair (web + worker), one identity, one API contract.
- Both legacy backends keep running until each domain is ported and the frontend switched; the LiveKit worker registry (`VOICE_BACKENDS_JSON`) allows all three to coexist under different labels.
- A data migration from Firestore and the b2b Supabase project is required (Phase 8 of the plan).
