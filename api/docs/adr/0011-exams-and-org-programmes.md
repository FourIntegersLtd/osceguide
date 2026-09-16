# 0011. `exams` and `org_programmes` are two tables, not one

Date: 2026-09-16
Status: accepted

## Context
Both products have something called an exam, and they are not the same thing.

In b2c, `app_type` is a published exam framework — `sca`, `plab`, `casc`, `ortho`, four of them,
effectively forever. It selects one of four parallel Firestore collections per entity through a
4×20 `COLLECTION_MAPPING` table, and it arrives from the client in `localStorage`, which is why
a `before_request` hook exists to catch the client lying about it.

In b2b, `b2b_exams` is an org-scoped row saying "this institution runs PLAB prep", carrying its
own status and import provenance. Two institutions running PLAB have two rows.

Merging them, as an earlier draft proposed, forces one of two wrong answers: the four platform
frameworks become org-scoped, or org programmes become global.

## Decision
`exams` is a platform table of four seeded rows binding a framework id, a feedback model key,
default timers and the station attempt limit. `org_programmes` is org-scoped, references an
exam, and carries status and import provenance. The exam a request concerns is derived from the
resource, never sent by the client as ambient state.

`compat/legacy_app_types.py` is used by the migration only, then deleted.

## Consequences
- The four frameworks are seeded data with real foreign keys, not a string compared against a
  hardcoded tuple in two codebases.
- Adding a fifth exam is a row and a framework, not another twenty collection names.
- `enforce_tenant_app_type` disappears: there is nothing for a client to lie about.
- Org programme features (import from the platform catalogue, per-org status) stay org-scoped
  without dragging the platform catalogue into a tenancy boundary it does not belong in.
