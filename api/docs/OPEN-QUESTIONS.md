# Open questions

Collected while building unattended. Nothing here blocked progress: each one
names the choice I made, so answering it is a change, not a start.

| # | Question | What I did | Cost to change |
|---|---|---|---|
| D-6 | Who owns the exam clock? Today it is the supervisor's browser (b2b, peer-to-peer over LiveKit packets) and `localStorage` (b2c, candidate-editable). | Left unimplemented. Slots carry nullable `phase`, `phase_started_at`, `phase_ends_at` so server-owned timing needs no migration. | Low |
