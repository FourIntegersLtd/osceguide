# 0007. Tests run against a real database; no in-memory store

Date: 2026-09-15
Status: accepted

## Context
b2b kept a 2,150-line in-memory reimplementation of its persistence layer, switched on by detecting pytest. Most tests exercised that copy, so the real repositories were largely untested and free to drift. b2c patched a mocked Firestore client per import site, so tests asserted on call arguments rather than data.

## Decision
Repository, HTTP and contract tests run against Postgres started by testcontainers (or `TEST_DATABASE_URL` in CI). Alembic upgrades the database to head once per session; each test runs inside a transaction that is rolled back. Only `domain.py` code is unit-tested without a database. External services are faked through `core/ports.py` protocols, never by patching module attributes.

## Consequences
- Tests prove SQL, constraints and migrations, not a stand-in.
- Local runs need Docker; CI uses a Postgres service container.
- Test data is set up through repositories and services, which doubles as a check that they compose.
