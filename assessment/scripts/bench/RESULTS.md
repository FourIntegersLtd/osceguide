# Voice bench results

The harnesses print their tables to the terminal and keep full transcripts only
under `runs/`, which is gitignored. This file is the durable record: every run
that decided a model or a prompt, what it measured and what was chosen. Add the
next run at the top of its section, with the commit that acted on it.

Two harnesses:

- `scripts/model_bench.py` replays a fixed doctor script against a persona. Arms
  are models, or one model with different instructions (`--instructions-file`).
- `scripts/debrief_bench.py` lets a Claude model play the trainee being
  debriefed, because a debrief is led by the trainee and cannot be scripted. Arms
  are prompt variants in `bench/debrief/variants`.

Both are judged by `claude-opus-5`, a different family from anything under test.

**Reading the numbers.** At 3 consultations per arm the judge alone moves role
breaches by about ±0.7 per consultation: re-scoring identical transcripts gave
0.0 on one pass and 0.7 on another. Treat a difference under about one breach as
noise unless the sample is larger.

## Voice models (`model_bench.py`, 2026-09-15)

3 consultations per arm, `reasoning_effort=none`, prompt and reminder identical
across arms.

| Persona | Arms | Result | Chosen |
|---|---|---|---|
| Simulated patient | `gpt-4o-mini`, `gpt-5.4-nano` | Tied on role adherence and quality. Nano cost $0.0118 against $0.0064 per consultation (+84%), was slower (TTFT 0.85s against 0.63s) and wrote about twice the output tokens | `gpt-4o-mini` stays |
| Debrief tutor | `gpt-4o`, `gpt-5.4-mini`, `gpt-5.4-nano` | 5.4-mini: fewer breaches, persona consistency 4.7 against 4.0, equal quality, slightly faster, $0.0220 against $0.0935 (-76%). Nano was cheaper still but quality fell to 3.3 | `gpt-5.4-mini` |

Nano's list price is lower, but it writes about twice the output tokens at about
twice the output rate, and that outweighs its cheaper cached input. The examiner
is not a separate arm: examiner stations dispatch in patient mode. The consulting
doctor shares the tutor tier and inherited `gpt-5.4-mini` without its own model
comparison; `VOICE_TUTOR_LLM=gpt-4o` reverts it without a deploy.

## Patient role lock (`model_bench.py`, 2026-09-16, `91fc712`)

Model held at `gpt-4o-mini`, instructions varied.

| Prompt | Role breaches per consultation |
|---|---|
| Old patient prompt | 2.7 |
| Role-locked prompt (shared `_blocks` role block, fenced clinical content) | 0.0 |

The drift came from the prompt, not the model. A per-turn role reminder was
also tried and showed no measurable benefit at 40 turns on the patient. On the
consulting doctor it made things worse, so it was removed. Do not reintroduce it
without a run.

## Consulting doctor, Athena (`athena_doctor.py`, `model_bench.py`, 2026-09-16)

`gpt-5.4-mini`, 3 consultations per run, script
`bench/patient_consulting_doctor.json`. Each row is the run that justified that
commit. Coverage is the share of plan sections spoken: core (what the patient
must not leave without) and plan (the rest).

| Commit | Change | Core coverage | History before management | Red flags | Other |
|---|---|---|---|---|---|
| `91fc712` | Plan tagged by audience and priority; the station's inlined question list removed | – | 75% → 100% | 100% | Meds and ICE 100%, unchanged. Given a checklist, the model had rushed the history to get through it |
| `4a52cd3` | Earned-information rule: name nothing the patient has not said | – | – | – | No bench figures; fixed from a live consultation |
| `f364522` | A history rather than a survey: depth floor on the presenting complaint, explicit red-flag screen, acknowledgement rule | 88% → 100% | 67% → 100% | 100% | Quality 2.3 → 3.0, persona 3.7 → 4.0. Breaches read 2.7 → 5.0, but the flagged lines were the doctor repeating what the scripted patient had said, which the judge counts against `DOCTOR_NEVER` |
| `42d35c3` | The next question is the acknowledgement; Phase 3 explains one point per turn | 100% | 100% | 100% | Breaches 5.0 → 4.0; output tokens 1889 → 1320 |
| `aa67c20` | Pacing clock (`consultation_pacing.py`) | 100% | 100% | 100% | Meds and ICE 100%, persona 4.0, breaches 2.7. The first draft read as leave to trim: coverage 94%, red flags 67%, until it was made conditional |
| `dff6cc9` | The clock can slow the doctor down as well as hurry it; the ladder takes any plan item | 100% | 100% | 100% | Meds and ICE 100%, persona 4.0, breaches 2.7 → 2.3. A first attempt handed out the diagnosis mid-history (history before management 0%) |

The bench has no wall clock, so pacing itself was checked with a timed run on
`make dev-assistant`, not here. `dff6cc9` came from a real 12-minute station that
finished in 5:20.

## Debrief tutor prompt (`debrief_bench.py`, 2026-09-27)

**Outcome: `walkthrough_v2` shipped, replacing Pendleton.** The debrief is now a
walk through the station's management plan, built together (PEARLS, with
Advocacy-Inquiry for gaps). The tutor may play the patient briefly for one moment
the trainee asks to practise. The only allowance for that is the `exception`
line in its role lock. The greeting now maps the debrief in one line. Four runs
led there, all with the same setup as r1 below: 2 scenarios, 4 personas and 2
repeats per arm.

### The shipped prompt against the old one

The r2 baseline is the Pendleton prompt. "Shipped" is 16 debriefs on the
production prompt after the change, at a cost of $2.10.

| | Pendleton (r2 baseline) | Shipped walkthrough |
|---|---|---|
| Opened with structure | 0.00 | 1.00 |
| Safety gap addressed | 0.44 | 1.00 |
| Trainee named takeaways | 0.50 | 0.94 |
| Clinical teaching (1-5) | 3.19 | 4.00 |
| Generic turns per debrief | 0.69 | 0.00 |
| Clinical errors | 0.19 | 0.06 |
| Breaches | 0.31 | 0.12 |
| Invented facts | 0.00 | 0.12 |
| Interrogation (1-5, lower better) | 2.06 | 2.12 |
| Trainee-led (1-5) | 4.06 | 3.81 |
| Tutor share of words | 59% | 51% |
| Longest tutor turn (words) | 139.9 | 89.7 |
| Felt safe / understands plan | 4.94 / 4.88 | 4.88 / 4.94 |
| Composite | 0.74 | 0.77 |

The shipped run is still flagged by one gate: in 1 of 16 debriefs the tutor
invented a detail while playing the patient. The prompt now tells it to keep the
patient vague rather than fill a gap, but that did not remove it entirely. Watch
for it in live debriefs.

### Blinded pairwise (`pairwise`, r2 debriefs, 16 matched pairs each)

| First | Second | Result |
|---|---|---|
| walkthrough_v2+timer | baseline (Pendleton) | 12 – 4 |
| walkthrough_v2+timer | walkthrough_v2 | 9 – 7 |
| walkthrough_v2+timer | r2c2_v2+timer | 7 – 9 |

The 12 – 4 preference cited in `debrief_prompt.py` was measured on the `+timer`
arm, which adds the bench's pacing notices. The shipped prompt carries the
walkthrough without them. The walkthrough and R2C2 were within a pair of each
other. The runs do not record why the walkthrough was picked over R2C2; on
r2's numbers R2C2+timer built slightly more of the plan together.

### Run r2: second-generation variants

80 debriefs, all completed, $10.79. The `_v2` variants were revised after r1:
- the practice moment starts at one agreed moment;
- the tutor uses the patient's own words and adds no backstory;
- it steps out explicitly afterwards.

| Variant | Clinical teaching | Built together | Missed | Safety gap | Takeaways | Invented | Breaches | Composite | Gate |
|---|---|---|---|---|---|---|---|---|---|
| walkthrough_v2 | 4.25 | 0.46 | 0.24 | 1.00 | 1.00 | 0.06 | 0.06 | 0.78 | invents more; 1 role-play unclean |
| walkthrough_v2+timer | 4.19 | 0.52 | 0.22 | 1.00 | 1.00 | 0.12 | 0.00 | 0.78 | invents more |
| r2c2_v2+timer | 4.25 | 0.56 | 0.21 | 1.00 | 0.94 | 0.12 | 0.19 | 0.77 | invents more; 1 role-play unclean |
| r2c2_v2 | 4.00 | 0.50 | 0.28 | 0.94 | 1.00 | 0.19 | 0.19 | 0.77 | invents more; 1 role-play unclean |
| baseline (Pendleton) | 3.19 | 0.40 | 0.36 | 0.44 | 0.50 | 0.00 | 0.31 | 0.74 | passes |

The Pendleton baseline passed the invention gate here because it never
role-plays, so it never invents as the patient. In r1's gate log, its breaches
were replaying the patient's lines unasked. The gate
compares invention against a baseline that avoids the risky behaviour
altogether. So the ship decision weighed the gated margin (0.06–0.12 invented
facts per debrief) against the teaching and safety gains, rather than being
read straight off the gate.

### Re-scoring r1 (`rejudge`)

Re-judging the same r1 transcripts changed which arms passed. r2c2 went from
blocked to passing. walkthrough and walkthrough_conversational picked up a
clinical-error block. Invention and breach counts moved by up to 0.12 per
debrief. With counts this small, gate verdicts from one judge pass are not
stable, which is why r2 and the pairwise judgements followed.

### Run r1: first-generation variants

Tutor `gpt-5.4-mini` on the production prompt with one variant's blocks swapped
in. Trainee `claude-sonnet-5`, judge `claude-opus-5`. There were 2 scenarios
(`chest_pain`, `new_type2_diabetes`), 4 trainee personas (`anxious`,
`overconfident`, `terse`, `just_tell_me`) and 2 repeats per variant, for 80
debriefs. 77 completed. Three failed with a 400 error when the trainee was sent
an empty message (aloba once, r2c2 twice). Cost $9.81.

| Variant | n | Built together | Missed | Interrogation (1-5, lower better) | Trainee-led (1-5) | Opened with structure | Safety gap addressed | Trainee named takeaways | Invented facts | Breaches | Composite |
|---|---|---|---|---|---|---|---|---|---|---|---|
| walkthrough | 16 | 0.47 | 0.26 | 1.62 | 4.19 | 1.00 | 0.94 | 1.00 | 0.06 | 0.19 | 0.80 |
| r2c2 | 14 | 0.43 | 0.32 | 1.64 | 4.14 | 1.00 | 0.93 | 0.93 | 0.14 | 0.07 | 0.79 |
| aloba | 15 | 0.41 | 0.26 | 1.87 | 4.40 | 1.00 | 1.00 | 1.00 | 0.20 | 0.13 | 0.79 |
| walkthrough_conversational | 16 | 0.44 | 0.27 | 1.81 | 4.12 | 1.00 | 1.00 | 1.00 | 0.19 | 0.19 | 0.78 |
| baseline (Pendleton) | 16 | 0.47 | 0.34 | 2.00 | 4.31 | 0.00 | 0.50 | 0.81 | 0.06 | 0.56 | 0.74 |

Trainee questionnaire and talk:

| Variant | Felt safe | Felt quizzed | Understands plan | Tutor share of words | Questions per turn | Stacked questions |
|---|---|---|---|---|---|---|
| walkthrough | 4.81 | 2.00 | 5.00 | 55% | 0.51 | 0.03 |
| r2c2 | 4.86 | 1.57 | 4.93 | 56% | 0.46 | 0.02 |
| aloba | 4.93 | 1.87 | 4.93 | 57% | 0.63 | 0.07 |
| walkthrough_conversational | 4.75 | 1.94 | 4.94 | 56% | 0.63 | 0.04 |
| baseline (Pendleton) | 4.62 | 2.00 | 4.81 | 54% | 0.71 | 0.13 |

Gates rule a variant out whatever its composite. A variant is blocked if it
invents more facts, breaches more or makes more clinical errors than the
baseline, or if it leaves a role-play unclean or invents as the patient. Every
arm was blocked:

- walkthrough: 1 role-play not exited cleanly; 1 invented as the patient
- r2c2: invents more than baseline
- aloba: invents more than baseline; 2 role-plays invented as the patient
- walkthrough_conversational: invents more than baseline; 1 role-play not exited cleanly
- baseline: 1 role-play not exited cleanly

**Outcome:** no r1 variant was adopted. Every variant beat the baseline on
structure, safety-gap coverage, takeaways and breaches, but invented while
playing the patient or failed to step out of a role-play. That led to the
`_v2` variants in r2.
