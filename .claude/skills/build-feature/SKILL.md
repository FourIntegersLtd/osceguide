---
name: build-feature
description: Build any new feature, or change an existing behaviour, so it ships without breaking the rest. Use whenever a feature, screen, route, job or behaviour change is requested, before writing any implementation code. Spec matrix, arm check, sibling check, impact, failing tests, smallest build, proof with the owner's verify skill, reviews and the ledger.
---

# Build a feature

Start the work as, or hand it to, the owner for the paths (`.claude/OWNERS.md`) and read its rule
file (`.claude/rules/`). Work through the steps in order; each ends with something written down.

**Who does which step.** The owner agent does every step below, including the spec matrix, the
arm and sibling checks and the greps. The main thread writes one brief (goal, paths, what is ruled
out, which verify skill), spawns the owner, and does not read, grep or edit those paths while it
runs. When it returns, relay the result and put any product choice to the user; re-check only what
contradicts something already known.

1. **Spec matrix** (short; show the user anything that is a product choice, with a recommended
   default): roles allowed and refused; for each load: loading, empty, failed, paged; for each
   action: success, each error code, double submit, stale data; state over time (expiry,
   suspension, retire, retry); scale; out of scope.
2. **Arm check**: which arms render the files you touch (the capability `surfaces` list); every
   such arm's journey (`docs/CORE-JOURNEYS.md`) runs before done.
3. **Sibling check**: grep every other gate that asks the same question; change them together and
   add the row to the lifecycle matrix.
4. **Impact**: grep callers; list the guards and journeys that cover them.
5. **Failing tests** at the lowest level per matrix row. See each fail for the stated reason.
   Assert literal user-visible values; a test that passes with its imports stubbed is deleted.
6. **Smallest build**: reuse first, no new layer without a second caller, delete what is now dead,
   no shims. Follow the app's AGENTS.md (tiers, one HTTP client, branch on error codes, server-side
   authorisation); regenerate API types, never hand-declare them.
7. **Prove** with the owner's verify skill and the affected journeys. Then `quality-reviewer`
   and `reviewer` (opus) always, in parallel; `/security-review` too for auth, money or deletion. Fix findings before reporting done.
8. **Ledger**: update `docs/CORE-JOURNEYS.md` if a journey changed; flip any `docs/EXPERIENCE-GAPS.md`
   row you closed to `fixed <sha>`; anything you chose not to do becomes a row, not a TODO comment.

Stage by explicit path. No repo-wide formatters. No `git stash`. Commit only when asked.
