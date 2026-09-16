# 0009. Test-driven, the way the LiveKit layer was rebuilt

Date: 2026-09-15
Status: accepted

## Context
The `assessment-platform` rebuild succeeded on a method, not on tooling: its consumer-leakage guard landed in the first commit; fakes for every port shipped inside the package; the legacy test suites were re-run as oracles against the new code; prompt output was frozen as byte-identical golden snapshots; the e2e harness and parity script were built before parity was declared; every rollout widening was allow-listed and gated on that script; and no commit changed behaviour without a test in the same commit. The platform skeleton (Phase 0) was built alongside its tests rather than test-first.

## Decision
Every slice follows a fixed order: guard tests, contract tests, oracle and golden tests, domain unit tests, repository tests, then implementation to green, committed together. Platform-wide guards live in `tests/guards/`, are AST scans parametrised per file with planted-violation meta-tests, and run as their own CI step. Ports get a fake in `tests/support/fakes.py` in the same commit they are added. Cutover per domain is gated on parity (feedback models, `parity_run.py compare --evaluate`, migration verify) behind an allow-list that defaults to off.

## Consequences
- The API is designed as executable tests before any service exists, so the design is reviewed as behaviour.
- Legacy behaviour that must survive is named explicitly by the oracle tests that carry it over; anything without an oracle is a deliberate change.
- Guards shape code at the point of writing: the first one to bite moved the health check's `select 1` into a repository.
- Work is slower to start and faster to finish; the rule "no behaviour change without a test" is enforced in review, not by a tool.
