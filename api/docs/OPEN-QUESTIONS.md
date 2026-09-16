# Open questions

Collected while building unattended. Nothing here blocked progress: each one
names the choice I made, so answering it is a change, not a start.

| # | Question | What I did | Cost to change |
|---|---|---|---|
| D-6 | Who owns the exam clock? Today it is the supervisor's browser (b2b, peer-to-peer over LiveKit packets) and `localStorage` (b2c, candidate-editable). | Left unimplemented. Slots carry nullable `phase`, `phase_started_at`, `phase_ends_at` so server-owned timing needs no migration. | Low |
| E-1 | The `osce_assessment` engine is still a vendored subtree in both legacy backends, not a versioned dependency. Scoring cannot run until it is one. | `core.ports.Evaluator` defines the boundary and a fake proves the job against it; `attempts/evaluator.py` raises rather than guessing, so a deployment that tries to score without an engine says so. Needs `packages/osce_assessment/pyproject.toml`, a tag, and a deploy key. | Low — one adapter |
| E-2 | Which marking model? b2c uses `gpt-5-mini` at `low` effort, b2b `gpt-4o` with effort unset. Results are not comparable. | `exams.feedback_model_key` is a column, defaulted to `'default'`, so this is a data change rather than a code change once you decide. | Low |
| E-3 | Org feedback templates narrow the platform schema, and the policy version becomes `<templateId>@<version>`. Not yet wired into `scoring.policy_for`. | Defaults to `platform-default@1`. The per-attempt policy is read from the frozen definition, so wiring it later changes no past attempt. | Low |
