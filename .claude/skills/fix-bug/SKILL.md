---
name: fix-bug
description: Fix a defect at its root cause and close the gap that let it through. Use whenever something is reported broken, wrong or regressed. Reproduce with a failing test, fix the cause, name the kind of bug and the CI check that should have caught it, and add or extend that check in the same change.
---

# Fix a bug

Start as, or hand to, the owner for the paths (`.claude/OWNERS.md`); read its rule file first.

1. **Reproduce with a failing test** at the lowest level that shows it (in a browser first if it is
   a screen). No test, no fix.
2. **Fix the root cause**, not the symptom; the smallest change, in the right layer.
3. **Name the kind** (1-13 in `docs/REGRESSION-PLAN.md`, "What the deep dive found") **and the Part 1
   check that should have caught it. If none exists, add or extend one in the same change.** Say
   both in the report.
4. **Prove** with the owner's verify skill, plus the journeys that cover the area.
5. If a fix introduced it, the commit message says "caused by <sha>".
6. Run `quality-reviewer`; add `reviewer` (opus) for auth, money or deletion.
