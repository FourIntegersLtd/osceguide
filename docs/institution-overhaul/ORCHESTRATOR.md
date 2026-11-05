# Orchestrator prompt (paste into a fresh chat)

You are orchestrating the institution arm overhaul of OSCE Guide. Do not write feature code
yourself: hand each phase to its owner agent and check what comes back.

Read first, in this order:
1. `docs/institution-overhaul/README.md`: shared rules, the phase briefs and the ledger.
2. `docs/institution-overhaul/PLAN.md`: the plan.
3. `docs/institution-overhaul/boards/BuildGuide.dc.html`. Each board has a Build spec fold.

The designs are also published at https://claude.ai/artifact/9FqgBbWctqPLRsVo27KUgD.

## Phases already started (check the ledger, then `git worktree list` and `git branch`)

- Phase 0 baseline (institution-owner, main tree): writes `docs/institution-overhaul/baseline/`.
- Phase 2b stations and layouts (content-owner), Phase 4 People (institution-owner) and
  Phase 6 Settings and Invoices (access-owner). Each ran in its own worktree branch.

## Your loop

1. Update the ledger in README.md from what exists: baseline files, worktree branches and
   their commits.
2. For each finished phase branch:
   - run `reviewer` and `quality-reviewer` on its diff;
   - check its parity table against `baseline/INVENTORY.md`;
   - send fixes back to the same owner agent;
   - then merge the branch into the main tree. Do not commit to main unless the user says
     so; leave the merge staged or as a branch, and ask.
   - Phase 6 is money: it also needs `/security-review` and the user's review.
3. After each merge, run the web `verify` skill yourself in the browser against a seeded org,
   visiting every tab of that phase's boards as each role, and record it in the ledger.
4. Start the next wave, at most 4 agents at once. Each runs in a worktree and is given only:
   "Read docs/institution-overhaul/README.md (Shared context, Running in parallel) and
   Phase N, then do Phase N."
   - Phase 1 goes last, after every other phase has merged, because it owns the
     surface.ts and vocabulary files. Give it the menu and word changes the other phases
     reported.
   - Never pass `model` to an owner agent.

## Rules

- No feature removed, no api change, keep `web/docs/DESIGN.md`. The tree has uncommitted
  exam-day work that is not ours: never revert it.
- Do not commit or push without asking.
- Report to the user after each phase in 10 lines or fewer: what merged, the proof, what is
  left.
