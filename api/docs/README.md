# platform-api docs

Read in this order if you are new.

| # | Document | What it answers |
|---|---|---|
| 1 | [GLOSSARY.md](GLOSSARY.md) | What the words mean. A cohort is not a trainee group; a slot is not an attempt. Also: the nine tokens the build rejects, and what to say instead. |
| 2 | [ATTEMPT-LIFECYCLE.md](ATTEMPT-LIFECYCLE.md) | One attempt traced across browser, API, engine, LiveKit, worker and job queue. The flow that crosses every boundary. |
| 3 | [ENVIRONMENT.md](ENVIRONMENT.md) | Every setting, what breaks without it, and why secrets have no defaults outside local. |
| 4 | [DATA-MODEL.md](DATA-MODEL.md) | Every table, column by column, with the reasoning behind each constraint. |
| 5 | [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to add a slice, tests first. The method, in order. |
| 6 | [adr/](adr/) | The decisions someone might otherwise question. |
| — | [DEPLOY-CHECKLIST.md](DEPLOY-CHECKLIST.md) | Gates before shipping platform-api to staging or production (migrations, voice label, classic Railway isolation). |
| — | [SUPPORT-RUNBOOK.md](SUPPORT-RUNBOOK.md) | What a platform admin does about the tickets that actually arrive. |
| — | [../../web/docs/BACKLOG.md](../../web/docs/BACKLOG.md) | All pending work and open questions, for every live repo. |
| — | [security/](security/) | The 2026-09 security assessment and the penetration test plan. |

1–4 are also published as one searchable page:
**https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ**

## Keeping these true

`DATA-MODEL.md` carries a standing rule at the top: **a migration and that document
change in the same commit.** The same applies to the rest of this folder whenever the
thing it describes moves.

Two of these are machine-checked in CI: `scripts/check_slice_readmes.py` enforces
slice README headings, and `scripts/check_data_model.py` (`make data-model`) diffs
`DATA-MODEL.md` against `Base.metadata`.

What no checker can hold is the *reasoning* — why a delete rule is `RESTRICT`, why a
unique index is partial, why a column is JSON. When a constraint changes, change the
sentence that explains it, or the next engineer implements against a rationale that no
longer holds.
