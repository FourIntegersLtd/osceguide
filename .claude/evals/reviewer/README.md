# Reviewer eval

Does the `reviewer` agent catch the bugs this repository has actually shipped? Each bug case
in `cases.jsonl` is a commit that introduced a real bug, with the bug in one sentence from the
commit that fixed it. Each clean case is a commit with no known bug, where every blocking
finding is a false alarm. (A "clean" commit may hide a bug nobody found, so treat its count as
an upper bound.)

```bash
.claude/evals/reviewer/run.sh <label>              # all cases, 3 at a time, ~1 min each
.claude/evals/reviewer/run.sh <label> <id> <id>    # just these
```

Each case checks its commit out in a throwaway worktree, lays today's `.claude/rules/` over it,
and runs today's `.claude/agents/reviewer.md` on Opus. A Haiku judge scores the review.
`results/<label>/summary.json` holds `caught/bugs`, `false_alarms` and the missed ids; the
review text (`*.md`) is not committed.

**Rerun** after any change to `reviewer.md`, `quality-reviewer.md`, the rule files' "What a
failure looks like here" sections, or the reviewer's model. Keep the change only if catches
hold or rise without more false alarms. One run is about 22 Opus reviews.

**Cases grow by themselves.** `fix-bug` writes "caused by <sha>" in every fix's commit message.
`sync_cases.sh` turns each such commit with no case yet into one JSON line
`{id, kind: "bug", sha: <commit that introduced it>, fix_sha, files, bug}`, with Haiku writing the
id and bug sentence; `--score` then runs the reviewer on the new cases, and a miss there is the
most useful thing to improve the reviewer on. SessionStart (`quality-gate.sh`) counts the fixes still
waiting and says so. Read each added line before committing it.

Fixes without a "caused by" line: `find_candidates.sh [since]` blames the lines they changed to
suggest the causing commit; confirm each pair by reading both diffs, then add the line by hand.
