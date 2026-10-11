---
name: fix-experience-gaps
description: Fix the next batch of rows from docs/EXPERIENCE-GAPS.md (the single list of everything that breaks a user's experience) and tick them off. Use whenever asked to fix experience gaps, work through the audit, or continue the fix loop; never re-audit an area before reading its rows.
---

# Fix experience gaps

**Retiring:** delete this skill once every row in `docs/EXPERIENCE-GAPS.md` is fixed or has a written reason; new work goes through `build-feature` and `fix-bug`.

`docs/EXPERIENCE-GAPS.md` is the queue and the ledger. No session holds the whole list; each
reads only the rows it will fix, and ends by updating the file. Usage:
`/fix-experience-gaps <area letter or "1"> [n]` (default n = 6).

## The loop

1. Read section 1 (BLOCKS) and the named area's section only. Take the first `n` rows whose
   status is `open` or `decided`, BLOCKS first.
2. Hand the batch to the owner for that area: `institution-owner` for B, R, T, P, H and the
   org-lifecycle S rows; `access-owner` for A, E and the entitlement, billing, close-account
   and erasure S rows; `content-owner` for C, station and media rows; `marking-owner` for
   scoring rows (R-5, S-2, S-8); `web-foundation-owner` for F rows and section 11; `attempt-engine-owner` for voice and runner rows; `staff-console-owner` for staff-console rows. Opus for
   anything touching auth, money or security; Sonnet otherwise. Up to three owners at once,
   on lanes that do not share files.
3. Each row: write the test first and watch it fail for the stated reason, then fix the root
   cause (no guard that silences the symptom). The test asserts the literal user-visible
   behaviour (a BLOCKS row gets a test that would fail if it came back). Then run the
   owner's verify skill at the level the row needs. A row the owner
   cannot fix stays open with a one-line reason in the ledger, never dropped.
4. The owner commits its own files only, with `git commit -m "..." -- <paths>` (after
   `git add <paths>`), one commit per batch, the row IDs first in the message. Never
   `git stash`, `git checkout`, `git restore` or `git reset`. It never edits `docs/EXPERIENCE-GAPS.md`; the main session
   flips statuses (`fixed <commit>` plus the test name) and appends to the Sessions log.
   Before the main session pushes, it proves HEAD in a clean worktree (`git worktree add
   --detach <scratchpad>/wt HEAD`, run `make ci` there with the main checkout's venv on PATH):
   the shared tree carries other sessions' uncommitted files, so a green run in it says nothing
   about the commit. `make ci` must run the same commands as the workflow; when CI adds a step,
   add it to the Makefile in the same commit (2026-10-11: the product-guide check was in CI only).
5. Run `quality-reviewer` on the round's diff, and the `reviewer` agent (opus) as well on
   every BLOCKS, auth or money row; act on both sets of findings before the next round.
   Then run the journey specs the batch touches, from `web/`: `npm run e2e:train` and/or
   `npm run e2e:assess`, against a local platform-api on :8002, never a remote one (see
   `docs/CORE-JOURNEYS.md` for prerequisites and which journeys need LiveKit). A failing
   journey is fixed or becomes a new row; never weaken the spec.
6. `/clear`, then repeat.

## Rules

- A row that needs a request or response schema change regenerates `api/openapi.json` and
  `web/src/foundation/platform-client/schema.d.ts` in the same commit (one session at a time
  on those two files).
- Every new row records whether a fix caused it (cite the commit) or not ("not caused by
  tonight's fixes"), so regressions are told apart from newly found gaps.
- Never edit a file another session has uncommitted changes in (`git status --short`).
- Order of areas: 1, B, R, T, C, A, S, E, P, H, then section 11 (mechanical: `worker`).

## Closing an area

When an area has no open rows, re-run its enumeration sweep (an `Explore` agent, model
sonnet, with the prompt: "For every page, route and role in <area>, list every load, action
and error code; for each, what the user sees on success, on each failure, and with the wrong
role; report only what breaks, misleads or dead-ends, with file:line") against the fixed
tree. Add any new row before marking the area `closed on <commit>` in its heading. Section
12 (the staging run) is the only remaining source of unknowns.
