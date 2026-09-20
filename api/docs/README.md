# platform-api docs

Read in this order if you are new.

| # | Document | What it answers |
|---|---|---|
| 1 | [GLOSSARY.md](GLOSSARY.md) | What the words mean. A cohort is not a trainee group; a slot is not an attempt. Also: the nine tokens the build rejects, and what to say instead. |
| 2 | [ATTEMPT-LIFECYCLE.md](ATTEMPT-LIFECYCLE.md) | One attempt traced across browser, API, engine, LiveKit, worker and job queue. The flow that crosses every boundary. |
| 3 | [SYSTEM-MAP.md](SYSTEM-MAP.md) | Which repo owns what, which are frozen, what this backend depends on, and the two false alarms that waste a week. |
| 4 | [ENVIRONMENT.md](ENVIRONMENT.md) | Every setting, what breaks without it, and why secrets have no defaults outside local. |
| — | [DEPLOY-CHECKLIST.md](DEPLOY-CHECKLIST.md) | Gates before shipping platform-api to staging or production (migrations, voice label, classic Railway isolation). |
| 5 | [DATA-MODEL.md](DATA-MODEL.md) | All 57 tables, column by column, with the reasoning behind each constraint. |
| 6 | [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to add a slice, tests first. The method, in order. |
| 7 | [adr/](adr/) | The decisions someone might otherwise question. 0010–0013 are the current shape. |
| 8 | [STATUS.md](STATUS.md) | Where the rebuild stands. The lower half is generated — trust it over the prose. |
| 9 | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) | What still needs a human answer. |
| — | [HANDOVER.md](HANDOVER.md) | If you are picking this up cold with nobody to ask. |

All of 1–5 are also published as one searchable page:
**https://claude.ai/artifact/DdGp1umMckFMvBiiMaLPWQ**

## Keeping these true

`DATA-MODEL.md` carries a standing rule at the top: **a migration and that document
change in the same commit.** The same applies to the rest of this folder whenever the
thing it describes moves.

Two of these are already machine-checked — `scripts/check_slice_readmes.py` enforces
slice README headings, and `scripts/status_report.py --check` fails when STATUS drifts.
The others are not yet. The next one worth automating is `DATA-MODEL.md`: a checker
that imports `Base.metadata` and diffs table and column names against the document.

What no checker can hold is the *reasoning* — why a delete rule is `RESTRICT`, why a
unique index is partial, why a column is JSON. When a constraint changes, change the
sentence that explains it, or the next engineer implements against a rationale that no
longer holds.
