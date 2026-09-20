# AI practice — B2C parity checklist

Manual verification: legacy `frontend/src/b2c` vs `platform-web` train (and assess self-practice after unification).

## Per exam (`sca`, `plab`, `casc`, `ortho`)

For each exam, run **mock session (≥2 stations)** and **library practise** (single station).

| Step | What to check |
|------|----------------|
| 1 Reading | Doctor brief sections match exam layout; reading timer; helper copy under CTAs |
| 2 Consultation | Confirm modal on "Start simulation" / tab 2; two-column layout; mic preflight; end consultation confirm |
| Timer | Reading expiry enters consultation preflight without dispatching voice; simulation time-up → next station or complete flow |
| Nav | Next station / skip labels on reading step; complete session hidden on feedback tab |
| 3 Management | Model answer visible in review only |
| 4 Feedback | Three sub-tabs with icons; green dot on step 4 when marked; debrief + info |
| Modals | Marking modal (SCA tips / generating animation); complete session confirm |
| Leave | Leave consultation copy matches B2C while live |

## Modal trigger checklist

- [ ] Start consultation confirm
- [ ] Reading expiry enters consultation preflight
- [ ] End consultation confirm (in panel)
- [ ] Leave consultation (navigation while live)
- [ ] Simulation time up → next / complete mock
- [ ] Marking your consultation (+ continue without waiting)
- [ ] End session (complete mock confirm)
- [ ] Debrief info
- [ ] Debrief session and practice as patient

## Implemented (2026-09-20)

- Original microphone preflight and Athena idle states, real LiveKit Room attachment,
  microphone-denial handling, duplicate-start guards and retry reuse of a created attempt.
- Reading/consultation flow, leave and completion confirmation, interactive marking tips.
- Exam-specific briefs and management screens, including all four Ortho station types
  and station comments; PLAB/CASC/Ortho feedback renderers ported from B2C.
- Patient-practice opening sentence, history, ICE and persona from the owner-only
  post-consultation API. Library practice can start a debrief; mock quotas stay on
  the station-set endpoint.
- Feedback history across attempts; paginated debrief history uses source consultation
  IDs and station/set scope instead of the latest debrief's own ID.
- Persistent live coverage and show/hide preference, plus saved coverage beside feedback.
  Requires API migration `h9i0j1k2l3m4` and a worker consuming `coverage`, `scoring`,
  and `summaries` queues.

## Verification Evidence

- Frontend unit suite: 186 passing; six focused exam-rendering tests pass after
  PLAB schema correction (including two new total/pass tests). TypeScript passes.
- Focused API suite: 30 passing, covering script privacy, early-access refusal,
  debrief prerequisites/history pagination, coverage persistence/grounding,
  duplicate processing and station-set flow. Scoped architecture guards: 643 pass.
- Scoped ESLint has no errors; existing hooks/configuration warnings remain.
  Mypy passes for six new/changed coverage, roleplay and history modules.
- Playwright: desktop reading, simulation, management, feedback and debrief chooser;
  patient history/ICE/persona using the real local roleplay API; mobile Start control.
- PLAB/CASC/Ortho feedback fixtures at 390px and 1440px: no page errors or horizontal
  overflow. Fixture feedback and transcript are browser-only, never persisted as marks.
- Screenshots: `/tmp/parity-*.png`; local practice worker completed pending marking
  and debrief-summary jobs.
- API smoke: 25/27 pass. The two starts return `station_not_published` for the
  selected local library fixture. The database documentation checker still reports
  unrelated peer-practice column documentation drift.
- Intentional correction to legacy PLAB presentation: individual scores are out
  of one, quotes may be arrays, and a missing serialized pass property is derived
  using the existing B2C model's total/domain rule rather than shown as failure.

## Remaining Acceptance Checks

The checkboxes above are deliberately not marked as live end-to-end passes.
Run a fresh microphone consultation, marking, debrief and patient roleplay for
each exam, including a two-station mock and library practice. Check timer expiry,
disconnect/retry, navigation, debrief quota exhaustion and live coverage against
real worker events. A side-by-side legacy-browser screenshot comparison is still
required before claiming pixel-perfect parity; source ports and fixture checks
alone are not that evidence.

## URLs

Mock: `?action=attempt|review&tab=patient|simulation|management|feedback&attempt={id}`

Deep link: `/attempts/{id}` → station feedback tab.
