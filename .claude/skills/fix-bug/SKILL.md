---
name: fix-bug
description: Fix a defect at its root cause and close the gap that let it through. Use whenever something is reported broken, wrong or regressed. Reproduce with a failing test, fix the cause, name the kind of bug and the CI check that should have caught it, and add or extend that check in the same change.
---

# Fix a bug

Start as, or hand to, the owner for the paths (`.claude/OWNERS.md`); read its rule file first.

**Who does which step.** The owner agent does every step below, including the repro, the root-cause
trace and the greps. The main thread writes one brief (goal, paths, what is ruled
out, which verify skill), spawns the owner, and does not read, grep or edit those paths while it
runs. When it returns, relay the result and put any product choice to the user; re-check only what
contradicts something already known.

1. **Reproduce with a failing test** at the lowest level that shows it (in a browser first if it is
   a screen). No test, no fix.
2. **Fix the root cause**, not the symptom; the smallest change, in the right layer.
3. **Name the kind** (1-13 in `docs/REGRESSION-PLAN.md`, "What the deep dive found") **and the Part 1
   check that should have caught it. If none exists, add or extend one in the same change.** Say
   both in the report.
4. **Prove** with the owner's verify skill, plus the journeys that cover the area.
5. **Find the commit that caused it** (`git blame` the lines you fixed, at the parent commit). The commit
   message says "caused by <sha>". Once it is committed, `.claude/evals/reviewer/sync_cases.sh --score`
   turns it into an eval case, so the reviewer is scored on this bug from now on (SessionStart reminds you).
6. Run `quality-reviewer` and `reviewer` (opus) in parallel; add `/security-review` for auth, money or deletion.
